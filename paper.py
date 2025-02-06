import os
import regex
import threading
from modelclient import client2


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
        except:
            return ""


def chunk(content,
          separators=[
              "\n# ",
              "\n## ",
              "\n### ",
              "\n#### ",
              "\n##### ",
              "\n###### ",
              "\n= ",
              "\n== ",
              "\n=== ",
              "\n==== ",
              "\n===== ",
              "\n====== ",
              r"\section",
              r"\subsection",
              r"\subsubsection",
              r"\paragraph",
              r"\subparagraph",
          ]):
    pattern = '|'.join([f"({sep})" for sep in separators])
    temp_list = regex.split(pattern, content)
    return [i for i in temp_list if i is not None]


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
        yield (f"解读论文{file_Path}", answer)


def translation(string,
                extraPrompt,
                separators=[
                    "\n# ",
                    "\n## ",
                    "\n### ",
                    "\n#### ",
                    "\n##### ",
                    "\n###### ",
                    "\n= ",
                    "\n== ",
                    "\n=== ",
                    "\n==== ",
                    "\n===== ",
                    "\n====== ",
                    r"\section",
                    r"\subsection",
                    r"\subsubsection",
                    r"\paragraph",
                    r"\subparagraph",
                ]):
    judge = string.strip()
    if judge and judge != '\n' and string not in separators:
        translation = client2.chat.completions.create(
            model="glm-4-flash",
            messages=[{
                "role": "user",
                "content": f"{extraPrompt}：\n{string}"
            }])
        translation = translation.choices[0].message.content
        return translation
    else:
        return string


def process_part_of_list(string_list, start, end, result_list, extraPrompt):
    for i in range(start, end):
        result_list[i] = translation(string_list[i], extraPrompt)


def baseConversion(file_path, suffix, prompt, userMessage):
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
    chunk_size = length // num_threads
    for i in range(num_threads):
        start_index = length - (num_threads - i) * chunk_size if i else 0
        end_index = length - (num_threads - 1 - i) * chunk_size
        t = threading.Thread(target=process_part_of_list,
                             args=(content, start_index, end_index,
                                   result_list, prompt))
        threads.append(t)
        t.start()
    while any(thread.is_alive() for thread in threads):
        yield (userMessage, ''.join(result_list))
    for t in threads:
        t.join()
    converted_content = ''.join(result_list)
    with open(kb_file_path, mode='w') as f:
        f.write(converted_content)
    yield (userMessage, converted_content)


def translatePapertoChinese(file_Path):
    converter = baseConversion(file_Path, 'Chi', '将论文译为中文，仅需翻译，不作说明',
                               '将论文译为中文')
    for result in converter:
        yield result


def translatePapertoEnglish(file_Path):
    converter = baseConversion(file_Path, 'Eng', '将论文译为英文，仅需翻译，不作说明',
                               '将论文译为英文')
    for result in converter:
        yield result


def polishPaper(file_Path):
    converter = baseConversion(file_Path, 'Pol', '对论文进行Nature级别润色，仅需润色，不作说明',
                               '对论文进行Nature级别润色')
    for result in converter:
        yield result
