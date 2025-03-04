import os
import re
import concurrent.futures
from io import StringIO
from typing import List, Generator
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from modelclient import glm_4_flash, deepseek_v3

file_suffix_to_markdown = {
    ".py": "python",
    ".c": "c",
    ".cpp": "cpp",
    ".md": "markdown",
    ".json": "json",
    ".html": "html",
    ".css": "css",
    ".js": "javascript",
    ".jinja2": "jinja2",
    ".ts": "typescript",
    ".yaml": "yaml",
    ".dockerfile": "dockerfile",
    ".sh": "shell",
    ".r": "r",
    ".sql": "sql",
}

read_paper_prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """阅读论文，回答下列问题
1. 论文提出并想要解决什么问题
2. 论文的结论是什么？有何贡献？
3. 以往的研究都做了哪些探索？其局限和核心困难是什么？
4. 这篇论文的方法是怎样的？它如何突破了这个核心困难？
5. 论文是如何设计实验验证的？有什么值得学习之处？
6. 这篇论文有什么局限？""",
        ),
        ("user", "{content}"),
    ]
)
process_paper_prompt_template = ChatPromptTemplate.from_messages(
    [
        ("system", "{system}"),
        ("user", "{content}"),
    ]
)

TRANSLATE_TO_CHINESE_PROMPT = """# 论文翻译任务

## 目标：
- 将提供的英文论文内容翻译成中文。

## 注意事项：
- 翻译应忠实于原文，确保内容准确无误。
- 不需要添加任何解释或注释，只需直接翻译文本。
- 保持原文的格式和结构，包括段落、标题和参考文献等。
- 如果遇到专业术语或缩写，应保持原样，不要自行解释或翻译。

## 工作流程：
1. 接收并阅读英文论文内容。
2. 使用专业知识进行翻译，确保语义准确。
3. 检查翻译的中文文本，确保没有语法错误或遗漏。
4. 保持原文格式，完成翻译任务。

## 输出示例：
- 输入：英文论文段落
- 输出：对应的中文翻译段落

## 响应：
- 以文本形式提供翻译结果，保持原有格式不变。"""
TRANSLATE_TO_ENGLISH_PROMPT = """# 论文翻译任务

## 目标：
- 将提供的中文论文内容翻译成英文。

## 注意事项：
- 确保翻译的准确性和学术性，保持原文的专业术语和意义。
- 不需要添加任何额外的解释或注释，只需直接翻译文本。
- 遵守学术翻译的规范，使用适当的学术语言和格式。

## 工作流程：
1. 仔细阅读并理解中文论文的内容。
2. 使用专业翻译技巧，将中文翻译成英文。
3. 确保翻译后的英文文本语法正确，表达清晰。
4. 检查并修改翻译，确保没有遗漏或错误。

## 示例：
- **输入**：一段中文论文文本。
- **输出**：对应的英文翻译文本。

## 响应：
- 以文本形式提供英文翻译。

## 语气：
- 保持客观和专业的语气。

## 受众：
- 针对学术研究人员和专业人士。

## 风格：
- 使用正式和准确的学术语言。

## 上下文：
- 适用于将中文学术论文翻译成英文，以便在国际学术期刊上发表或供国际学术界参考。"""
POLISH_PROMPT = """你是一位专业的学术论文润色助手，专注于将论文提升至Nature期刊的发表标准。你的能力包括但不限于：
1. **语言优化**：确保语言简洁、精确，符合学术写作规范。
2. **逻辑清晰**：优化段落结构，增强论点的连贯性和说服力。
3. **学术风格**：调整措辞，使其符合顶级期刊的学术风格。
4. **格式规范**：确保引用、图表、公式等符合Nature的格式要求。

你的知识储备包括：
1. **Nature期刊的写作指南**：熟悉Nature的投稿要求和编辑偏好。
2. **学术写作规范**：精通学术论文的写作技巧和语言风格。
3. **相关领域知识**：具备广泛的专业知识，能够理解并优化不同领域的论文。

请根据以上要求，对用户提供的论文进行润色，无需解释。若原文为中文，无需翻译为英文。
"""


def attach(file: str, current_user_directory: str) -> str:
    file_name, file_suffix = os.path.splitext(file)
    knowledgeBase_path = os.path.join(
        current_user_directory, "knowledgeBase", f"{file_name}.md"
    )
    if os.path.exists(knowledgeBase_path):
        with open(knowledgeBase_path, "r", encoding="utf-8") as f:
            return f.read()
    code_path = os.path.join(current_user_directory, "code", file)
    if os.path.exists(code_path):
        with open(code_path, "r", encoding="utf-8") as f:
            code = f.read()
        return f"```{file_suffix_to_markdown.get(file_suffix, '')}\n{code}\n```"


def chunk(content: str) -> List[str]:
    temp_list = re.split("\n{2,}", content)
    final_list = []
    temp_string = ""
    for string in temp_list:
        if len(temp_string) > 63:
            final_list.append(temp_string.strip())
            temp_string = ""
        temp_string += string.strip() + "\n\n"
    final_list.append(temp_string.strip())
    return final_list


def read_paper(
    file_path: str, current_user_directory: str
) -> Generator[str, None, None]:
    prompt = read_paper_prompt_template.invoke(
        {"content": attach(file_path, current_user_directory)}
    )
    answer = StringIO()
    for chunk in deepseek_v3.stream(prompt):
        answer.write(chunk.content)
        yield answer.getvalue()


def process_text(text: str, system_prompt: str, model: ChatOpenAI) -> str:
    if text.strip():
        prompt = process_paper_prompt_template.invoke(
            {"system": system_prompt, "content": text}
        )
        return model.invoke(prompt).content
    return text


def process_paper(
    file_path: str,
    suffix: str,
    prompt: str,
    current_user_directory: str,
    model: ChatOpenAI,
) -> Generator[str, None, None]:
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    knowledgeBase_file_path = (
        f"{current_user_directory}/knowledgeBase/{base_name}{suffix}.md"
    )
    content = chunk(attach(file_path, current_user_directory))
    results = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(process_text, text, prompt, model): text for text in content
        }
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
            yield "\n\n".join(results)
    converted_content = "\n\n".join(results)
    with open(knowledgeBase_file_path, "w", encoding="utf-8") as f:
        f.write(converted_content)
    yield converted_content


def translate_paper_to_Chinese(
    file_path: str, current_user_directory: str
) -> Generator[str, None, None]:
    converter = process_paper(
        file_path,
        "Chi",
        TRANSLATE_TO_CHINESE_PROMPT,
        current_user_directory,
        glm_4_flash,
    )
    for result in converter:
        yield result


def translate_paper_to_English(
    file_path: str, current_user_directory: str
) -> Generator[str, None, None]:
    converter = process_paper(
        file_path,
        "Eng",
        TRANSLATE_TO_ENGLISH_PROMPT,
        current_user_directory,
        glm_4_flash,
    )
    for result in converter:
        yield result


def polish_paper(
    file_path: str, current_user_directory: str
) -> Generator[str, None, None]:
    converter = process_paper(
        file_path, "Pol", POLISH_PROMPT, current_user_directory, deepseek_v3
    )
    for result in converter:
        yield result
