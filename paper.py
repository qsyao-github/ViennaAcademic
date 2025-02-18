import os
import re
import threading
import time
from modelclient import client2, client5


def attach(file):
    filemd = file[:file.rfind('.')] + '.md'
    if filemd in os.listdir('knowledgeBase'):
        with open(f'knowledgeBase/{filemd}', 'r', encoding='utf-8') as f:
            return f.read()
    else:
        try:
            if file in os.listdir('paper'):
                with open(f'paper/{file}', 'r', encoding='utf-8') as f:
                    return f.read()
            elif file in os.listdir('code'):
                with open(f'code/{file}', 'r', encoding='utf-8') as f:
                    code = f.read()
                    if file.endswith('.py'):
                        return f"```python\n{code}\n```"
                    elif file.endswith('.cpp'):
                        return f"```cpp\n{code}\n```"
                    elif file.endswith('.java'):
                        return f"```java\n{code}\n```"
                    elif file.endswith('.c'):
                        return f"```c\n{code}\n```"
        except:
            return ""


def chunk(content):
    temp_list = re.split('\n{2,}', content)
    final_list = []
    temp_string = ""
    for string in temp_list:
        if len(temp_string) > 63:
            final_list.append(temp_string.strip())
            temp_string = ""
        temp_string += string.strip() + "\n\n"
    final_list.append(temp_string.strip())
    return final_list


def readPaper(file_Path):
    prompt = attach(file_Path) + '''阅读论文，回答下列问题
1. 论文提出并想要解决什么问题
2. 论文的结论是什么？有何贡献？
3. 以往的研究都做了哪些探索？其局限和核心困难是什么？
4. 这篇论文的方法是怎样的？它如何突破了这个核心困难？
5. 论文是如何设计实验验证的？有什么值得学习之处？
6. 这篇论文有什么局限？'''
    answer = ""
    stream = client2.chat.completions.create(model="glm-4-flash",
                                             messages=[{
                                                 "role": "user",
                                                 "content": prompt
                                             }],
                                             stream=True)
    for chunk in stream:
        answer += chunk.choices[0].delta.content or ""
        yield answer


def translation(string, extraPrompt):
    judge = string.strip()
    if judge:
        translation = client2.chat.completions.create(model="glm-4-flash",
                                                      messages=[{
                                                          "role":
                                                          "system",
                                                          "content":
                                                          extraPrompt
                                                      }, {
                                                          "role":
                                                          "user",
                                                          "content":
                                                          string
                                                      }])
        translation = translation.choices[0].message.content
        return translation
    else:
        return string


def process_part_of_list(string_list, start, end, result_list, extraPrompt):
    for i in range(start, end):
        result_list[i] = translation(string_list[i], extraPrompt)


def baseConversion(file_path, suffix, prompt):
    base_name = file_path[:file_path.rfind('.')]
    paper_file_path = f'paper/{base_name}{suffix}.md'
    kb_file_path = f'knowledgeBase/{base_name}{suffix}.md'
    if os.path.exists(paper_file_path):
        with open(paper_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    content = chunk(attach(file_path))
    length = len(content)
    threads = []
    result_list = [""] * length
    num_threads = min(length, 64)
    for i in range(num_threads):
        start_index = int(i * length / num_threads)
        end_index = int((i + 1) * length / num_threads)
        t = threading.Thread(target=process_part_of_list,
                             args=(content, start_index, end_index,
                                   result_list, prompt))
        threads.append(t)
        t.start()
    while any(thread.is_alive() for thread in threads):
        yield '\n\n'.join(result_list)
        time.sleep(1)
    for t in threads:
        t.join()
    converted_content = '\n\n'.join(result_list)
    with open(kb_file_path, mode='w') as f:
        f.write(converted_content)
    yield converted_content


def translatePapertoChinese(file_Path):
    prompt = """# 论文翻译任务

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
- 以文本形式提供翻译结果，保持原有格式不变。
"""
    converter = baseConversion(file_Path, 'Chi', prompt)
    for result in converter:
        yield result


def translatePapertoEnglish(file_Path):
    prompt = """# 论文翻译任务

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
- 适用于将中文学术论文翻译成英文，以便在国际学术期刊上发表或供国际学术界参考。
"""
    converter = baseConversion(file_Path, 'Eng', prompt)
    for result in converter:
        yield result


def polishPaper(file_Path):
    prompt = """# 角色：  
资深编辑，擅长论文润色和语法修正

# 背景信息：  
针对需要润色的学术论文，确保语言流畅性和学术规范性

# 工作流程/工作任务：  
1. 阅读并理解论文内容
2. 识别并修正语法错误
3. 提升句子结构和表达清晰度
4. 保持原论文的学术风格和语调

# 输出示例：  
- 原文： "This study shows that the effect of factor A on phenomenon B is significant."
- 润色后： "This study demonstrates a significant impact of factor A on phenomenon B."
- 原文：研究结果证明了我们的假设是正确的。
- 润色后：研究结果表明，我们的假设得到了证实。

# 注意事项：  
- 保持原文的研究目的和结论不变
- 遵循学术写作的规范和格式
- 确保润色后的文本符合学术期刊的要求
- 若原文为中文，不必译为英文
- 只提供润色后的文本，避免包括解释
"""
    converter = baseConversion(file_Path, 'Pol', prompt)
    for result in converter:
        yield result
