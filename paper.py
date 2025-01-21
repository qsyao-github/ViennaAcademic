import os
import regex
import threading
from modelclient import client2


def attach(file):
    filemd = file[:file.rfind('.')] + '.md'
    if filemd in os.listdir('knowledgeBase'):
        with open(f'knowledgeBase/{filemd}', 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        try:
            if file in os.listdir('paper'):
                with open(f'paper/{file}', 'r', encoding='utf-8') as f:
                    content = f.read()
        except:
            content = ""
    return content


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
    judge = string.lstrip().rstrip()
    if judge != '\n' and judge != '' and string not in separators:
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


def translatePapertoChinese(file_Path):
    if file_Path[:file_Path.rfind('.')] + 'Chi.md' in os.listdir('paper'):
        with open(f'paper/{file_Path[:file_Path.rfind(".")]}Chi.md',
                  'r',
                  encoding='utf-8') as f:
            content = f.read()
        return content
    content = chunk(attach(file_Path))
    input(str(content))
    length = len(content)
    threads = []
    result_list = [""] * length
    if length >= 64:
        chunk_size = length // 64
        for i in range(64):
            start_index = length - (64 - i) * chunk_size if i else 0
            end_index = length - (63 - i) * chunk_size
            t = threading.Thread(target=process_part_of_list,
                                 args=(content, start_index, end_index,
                                       result_list, "将论文译为中文，仅需翻译，不作说明"))
            threads.append(t)
            t.start()
    else:
        for i in range(length):
            t = threading.Thread(target=process_part_of_list,
                                 args=(content, i, i + 1, result_list,
                                       "将论文译为中文，仅需翻译，不作说明"))
            threads.append(t)
            t.start()
    while any(thread.is_alive() for thread in threads):
        yield ("将论文译为中文", ''.join(result_list))
    for t in threads:
        t.join()
    with open(f'knowledgeBase/{file_Path[:file_Path.rfind(".")]}Chi.md',
              mode='w') as f:
        f.write(''.join(result_list))
    yield ("将论文译为中文", ''.join(result_list))


def translatePapertoEnglish(file_Path):
    if file_Path[:file_Path.rfind('.')] + 'Eng.md' in os.listdir('paper'):
        with open(f'paper/{file_Path[:file_Path.rfind(".")]}Eng.md',
                  'r',
                  encoding='utf-8') as f:
            content = f.read()
        return ("将论文译为英文", content)
    content = chunk(attach(file_Path))
    length = len(content)
    threads = []
    result_list = [""] * length
    if length >= 64:
        chunk_size = length // 64
        for i in range(64):
            start_index = length - (64 - i) * chunk_size if i else 0
            end_index = length - (63 - i) * chunk_size
            t = threading.Thread(target=process_part_of_list,
                                 args=(content, start_index, end_index,
                                       result_list, "将论文译为英文，仅需翻译，不作说明"))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        with open(f'knowledgeBase/{file_Path[:file_Path.rfind(".")]}Eng.md',
                  mode='w') as f:
            f.write('\n'.join(result_list))
    else:
        for i in range(length):
            t = threading.Thread(target=process_part_of_list,
                                 args=(content, i, i + 1, result_list,
                                       "将论文译为英文，仅需翻译，不作说明"))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        with open(f'knowledgeBase/{file_Path[:file_Path.rfind(".")]}Eng.md',
                  mode='w') as f:
            f.write('\n'.join(result_list))
    return ("将论文译为英文", '\n'.join(result_list))


def polishPaper(file_Path):
    if file_Path[:file_Path.rfind('.')] + 'Pol.md' in os.listdir('paper'):
        with open(f'paper/{file_Path[:file_Path.rfind(".")]}Pol.md',
                  'r',
                  encoding='utf-8') as f:
            content = f.read()
        return ("润色论文", content)
    content = chunk(attach(file_Path))
    length = len(content)
    threads = []
    result_list = [""] * length
    if length >= 64:
        chunk_size = length // 64
        for i in range(64):
            start_index = length - (64 - i) * chunk_size if i else 0
            end_index = length - (63 - i) * chunk_size
            t = threading.Thread(target=process_part_of_list,
                                 args=(content, start_index, end_index,
                                       result_list,
                                       "对论文进行Nature级别润色，仅需润色，不作说明"))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        with open(f'knowledgeBase/{file_Path[:file_Path.rfind(".")]}Pol.md',
                  mode='w') as f:
            f.write('\n'.join(result_list))
    else:
        for i in range(length):
            t = threading.Thread(target=process_part_of_list,
                                 args=(content, i, i + 1, result_list,
                                       "对论文进行Nature级别润色，仅需润色，不作说明"))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        with open(f'knowledgeBase/{file_Path[:file_Path.rfind(".")]}Pol.md',
                  mode='w') as f:
            f.write('\n'.join(result_list))
    return ("润色论文", '\n'.join(result_list))
