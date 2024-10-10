import os
import re
from zhipuai import ZhipuAI
from openai import OpenAI
import time
import threading

client1 = OpenAI(api_key="sk-xCBtJ7y0e9Eg7kAR895b5b7739A4490386E0E0Fc6c2a18C9",
                 base_url="https://api.kenxu.top:5/v1")
client2 = ZhipuAI(api_key="1d24ec7d1a60b512b355ea27747f8e35.TQaJOi2u6ksywqwi")


def attach(file):
    filemd = file[:file.rfind('.')] + '.md'
    if filemd in os.listdir('knowledgeBase'):
        with open(f'knowledgeBase/{filemd}', 'r', encoding='utf-8') as f:
            content = f.read()
    elif filemd in os.listdir('userUpload'):
        with open(f'userUpload/{filemd}', 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        try:
            if file in os.listdir('paper'):
                with open(f'paper/{file}', 'r', encoding='utf-8') as f:
                    content = f.read()
            else:
                with open(f'userUpload/{file}', 'r', encoding='utf-8') as f:
                    content = f.read()
        except:
            print(f"文件{file}不存在")
            content = ""
    return content


def chunk(content,
          separators=[
              "\n#", "\n=", r"\section", r"\subsection", r"\subsubsection",
              r"\paragraph", r"\subparagraph"
          ]):
    pattern = '|'.join(map(re.escape, separators))
    return re.split(pattern, content)


def readPaper(file_Path):
    prompt = attach(file_Path) + '''阅读论文，回答下列问题
1. 论文提出并想要解决什么问题
2. 论文的结论是什么？有何贡献？
3. 以往的研究都做了哪些探索？其局限和核心困难是什么？
4. 这篇论文的方法是怎样的？它如何突破了这个核心困难？
5. 论文是如何设计实验验证的？有什么值得学习之处？
6. 这篇论文有什么局限？'''
    response = client1.chat.completions.create(model="gemini-1.5-flash",
                                               messages=[{
                                                   "role": "user",
                                                   "content": prompt
                                               }])
    return (f"解读论文{file_Path}", response.choices[0].message.content)


def translation(string, extraPrompt):
    judge = string.lstrip().rstrip()
    if judge != '\n' and judge != '':
        translation = client2.chat.completions.create(
            model="glm-4-flash",
            messages=[{
                "role": "user",
                "content": f"{extraPrompt}：\n{string}"
            }])
        translation = translation.choices[0].message.content
        print(translation)
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
    length = len(content)
    threads = []
    result_list = [None] * length
    if length >= 3:
        chunk_size = length // 3
        for i in range(3):
            start_index = length - (3 - i) * chunk_size if i else 0
            end_index = length - (2 - i) * chunk_size
            t = threading.Thread(target=process_part_of_list,
                                 args=(content, start_index, end_index,
                                       result_list, "将论文译为中文，仅需翻译，不作说明"))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        with open(f'paper/{file_Path[:file_Path.rfind(".")]}Chi.md',
                  mode='w') as f:
            f.write('\n'.join(result_list))
    else:
        for i in range(length):
            t = threading.Thread(target=process_part_of_list,
                                 args=(content, i, i + 1, result_list,
                                       "将论文译为中文，仅需翻译，不作说明"))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        with open(f'paper/{file_Path[:file_Path.rfind(".")]}Chi.md',
                  mode='w') as f:
            f.write('\n'.join(result_list))
    return ("将论文译为中文", '\n'.join(result_list))


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
    result_list = [None] * length
    if length >= 3:
        chunk_size = length // 3
        for i in range(3):
            start_index = length - (3 - i) * chunk_size if i else 0
            end_index = length - (2 - i) * chunk_size
            t = threading.Thread(target=process_part_of_list,
                                 args=(content, start_index, end_index,
                                       result_list, "将论文译为英文，仅需翻译，不作说明"))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        with open(f'paper/{file_Path[:file_Path.rfind(".")]}Eng.md',
                  mode='w') as f:
            f.write('\n'.join(result_list))
    else:
        for i in range(length):
            print(content[i])
            t = threading.Thread(target=process_part_of_list,
                                 args=(content, i, i + 1, result_list,
                                       "将论文译为英文，仅需翻译，不作说明"))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        with open(f'paper/{file_Path[:file_Path.rfind(".")]}Eng.md',
                  mode='w') as f:
            f.write('\n'.join(result_list))
    return ("将论文译为英文", '\n'.join(result_list))


def polishPaper(file_Path):
    if file_Path[:file_Path.rfind('.')] + 'Pol.md' in os.listdir('paper'):
        with open(f'paper/{file_Path[:file_Path.rfind(".")]}Pol.md',
                  'r',
                  encoding='utf-8') as f:
            content = f.read()
        return ("将论文译为英文", content)
    content = chunk(attach(file_Path))
    length = len(content)
    threads = []
    result_list = [None] * length
    if length >= 3:
        chunk_size = length // 3
        for i in range(3):
            start_index = length - (3 - i) * chunk_size if i else 0
            end_index = length - (2 - i) * chunk_size
            t = threading.Thread(target=process_part_of_list,
                                 args=(content, start_index, end_index,
                                       result_list,
                                       "对论文进行Nature级别润色，仅需润色，不作说明"))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        with open(f'paper/{file_Path[:file_Path.rfind(".")]}Pol.md',
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
        with open(f'paper/{file_Path[:file_Path.rfind(".")]}Pol.md',
                  mode='w') as f:
            f.write('\n'.join(result_list))
    return ("润色论文", '\n'.join(result_list))
