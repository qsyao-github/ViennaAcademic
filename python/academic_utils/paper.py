"""
论文模块
"""

import asyncio
import os
import re
from io import StringIO
from typing import AsyncGenerator, List, Literal

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai.chat_models.base import BaseChatOpenAI
from python.llm_utils.modelclient import deepseek_v3
from python.llm_utils.system_prompt import (
    POLISH_PROMPT,
    TRANSLATE_TO_CHINESE_PROMPT,
    TRANSLATE_TO_ENGLISH_PROMPT,
)
from python.semaphore import semaphore1024

"""chunk函数对文件分段，每段不宜小于63个字符"""
MIN_CHARACTER_THRESHOLD = 63
FILE_SUFFIX_TO_MARKDOWN = {
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


def attach(file: str, current_user_directory: str) -> str:
    """附加文件内容

    在knowledgeBase和code目录下查找文件。代码文件放入对应代码框中。由于参数是由Gradio端根据文件列表生成的，不应出现文件不存在的情况

    Parameters
    ----------
    file: str
        文件名
    current_user_directory: str
        当前用户根目录

    Returns
    ----------
    str
        文件内容。若为代码则放入代码框
    """
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
        return f"```{FILE_SUFFIX_TO_MARKDOWN.get(file_suffix, '')}\n{code}\n```"


def chunk(content: str) -> List[str]:
    """分段

    按换行符分段，确保每段长度大于63个字符

    Parameters
    ----------
    content: str
        文本内容

    Returns
    ----------
    final_list: List[str]
        分段后的文本
    """
    temp_list = re.split("\n+", content)
    final_list = []
    temp_string = ""
    for string in temp_list:
        if len(temp_string) > MIN_CHARACTER_THRESHOLD:
            final_list.append(temp_string.strip())
            temp_string = ""
        temp_string += string.strip() + "\n\n"
    final_list.append(temp_string.strip())
    return final_list


async def read_paper(
    file_path: str, current_user_directory: str
) -> AsyncGenerator[str, None]:
    """论文解读

    Parameters
    ----------
    file_path: str
        文件路径
    current_user_directory: str
        当前用户根目录

    Yields
    ----------
    str
        解读结果。Gradio不支持增量更新，每次均返回完整字符串
    """
    prompt = await read_paper_prompt_template.ainvoke(
        {"content": attach(file_path, current_user_directory)}
    )
    answer = StringIO()
    async for chunk in deepseek_v3.astream(prompt):
        answer.write(chunk.content)
        yield answer.getvalue()
    answer.close()


async def process_single_chunk(
    text: str, system_prompt: str, model: BaseChatOpenAI, index: int, result: List[str]
) -> None:
    """根据prompt处理文本

    Parameters
    ----------
    text: str
        待处理文本
    system_prompt: str
        系统提示词
    model: BaseChatOpenAI
        模型，目前都使用deepseek-v3
    index: int
        文本索引
    result: List[str]
        处理结果列表
    """
    if text.strip():
        prompt = await process_paper_prompt_template.ainvoke(
            {"system": system_prompt, "content": text}
        )
        result[index] = (await model.ainvoke(prompt)).content


def generate_output_path(
    file_path: str, suffix: Literal["Chi", "Eng", "Pol"], user_directory: str
) -> str:
    """生成输出文件路径

    Parameters
    ----------
    file_path: str
        文件路径
    suffix: Literal['Chi', 'Eng', 'Pol']
        文件后缀。分别对应英译中、中译英、润色
    user_directory: str
        用户目录

    Returns
    ----------
    str
        输出文件路径
    """
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    return f"{user_directory}/knowledgeBase/{base_name}{suffix}.md"


def generate_tasks(
    prompt: str,
    model: BaseChatOpenAI,
    processed_chunks: List[str],
    document_chunks: List[str],
    semaphore: asyncio.Semaphore,
) -> List[asyncio.Task[str]]:
    """产生任务列表

    Parameters
    ----------
    prompt: str
        系统提示词
    model: BaseChatOpenAI
        模型，目前都使用deepseek-v3
    processed_chunks: List[str]
        处理后的文本列表
    document_chunks: List[str]
        处理前的文本列表
    semaphore: asyncio.Semaphore
        信号量，用于控制并发数
    """
    return [
        worker(chunk, prompt, model, index, processed_chunks, semaphore)
        for index, chunk in enumerate(document_chunks)
    ]


def write_to_knowledge_base(output_path: str, content: str) -> None:
    """将处理结果写入知识库文件

    Parameters
    ----------
    output_path: str
        输出文件路径
    content: str
        处理结果
    """
    with open(output_path, "w", encoding="utf-8") as output_file:
        output_file.write(content)


async def worker(
    text: str,
    system_prompt: str,
    model: BaseChatOpenAI,
    index: int,
    result: List[str],
    semaphore: asyncio.Semaphore,
) -> str:
    async with semaphore:
        return await process_single_chunk(text, system_prompt, model, index, result)


async def process_paper(
    file_path: str,
    suffix: Literal["Chi", "Eng", "Pol"],
    prompt: str,
    current_user_directory: str,
    model: BaseChatOpenAI,
) -> AsyncGenerator[str, None]:
    """处理论文

    论文翻译、润色的抽象函数。

    Parameters
    ----------
    file_path: str
        文件路径
    suffix: Literal['Chi', 'Eng', 'Pol']
        文件后缀。分别对应英译中、中译英、润色
    prompt: str
        系统提示词
    current_user_directory: str
        当前用户目录
    model: BaseChatOpenAI
        模型，目前都使用deepseek-v3

    Yields
    ----------
    str
        已处理的文段。Gradio不支持增量更新，故返回完整字符串
    """
    # 初始化输出路径和内容块
    knowledgeBase_file_path = generate_output_path(
        file_path, suffix, current_user_directory
    )
    document_chunks = chunk(attach(file_path, current_user_directory))

    # 并行处理文本块
    processed_chunks = [""] * len(document_chunks)
    tasks = generate_tasks(
        prompt, model, processed_chunks, document_chunks, semaphore1024
    )
    for future in asyncio.as_completed(tasks):
        await future
        yield "\n\n".join(processed_chunks)
    # 写入最终结果并返回
    final_content = "\n\n".join(processed_chunks)
    write_to_knowledge_base(knowledgeBase_file_path, final_content)
    yield final_content


async def translate_paper_to_Chinese(
    file_path: str, current_user_directory: str
) -> AsyncGenerator[str, None]:
    """论文英译中

    Parameters
    ----------
    file_path: str
        文件路径
    current_user_directory: str
        当前用户目录

    Yields
    ----------
    str
        已处理的文段。Gradio不支持增量更新，故返回完整字符串
    """
    async for item in process_paper(
        file_path,
        "Chi",
        TRANSLATE_TO_CHINESE_PROMPT,
        current_user_directory,
        deepseek_v3,
    ):
        yield item


async def translate_paper_to_English(
    file_path: str, current_user_directory: str
) -> AsyncGenerator[str, None]:
    """论文中译英

    Parameters
    ----------
    file_path: str
        文件路径
    current_user_directory: str
        当前用户目录

    Yields
    ----------
    str
        已处理的文段。Gradio不支持增量更新，故返回完整字符串
    """
    async for item in process_paper(
        file_path,
        "Eng",
        TRANSLATE_TO_ENGLISH_PROMPT,
        current_user_directory,
        deepseek_v3,
    ):
        yield item


async def polish_paper(
    file_path: str, current_user_directory: str
) -> AsyncGenerator[str, None]:
    """论文润色

    Parameters
    ----------
    file_path: str
        文件路径
    current_user_directory: str
        当前用户目录

    Yields
    ----------
    str
        已处理的文段。Gradio不支持增量更新，故返回完整字符串
    """
    async for item in process_paper(
        file_path, "Pol", POLISH_PROMPT, current_user_directory, deepseek_v3
    ):
        yield item
