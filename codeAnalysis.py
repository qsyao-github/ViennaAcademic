import os
import subprocess
import time
from io import StringIO
from modelclient import client1 as client


def codegeex_generate(prompt):
    start = time.time()
    response = client.chat.completions.create(model="codestral-latest",
                                            messages=[{
                                                "role": "user",
                                                "content": prompt
                                            }])
    time.sleep(max(1, 4-time.time()+start))
    return response.choices[0].message.content


def codestral_stream(prompt):
    response = client.chat.completions.create(model="codestral-latest",
                                                messages=[{
                                                    "role": "user",
                                                    "content": prompt
                                                }],stream=True)
    finalResponse = StringIO()
    for chunk in response:
        finalResponse.write(chunk.choices[0].delta.content or "")
        yield finalResponse.getvalue()
    finalResponse.close()

def is_program_file(filename):
    program_extensions = frozenset({
        '.vue', '.js', '.ts', '.html', '.htm', '.css', '.jsx', '.c', '.cpp',
        '.cxx', '.cc', '.java', '.py', '.go', '.php', '.rs', '.sql', '.m',
        '.mm', '.kt', '.swift', '.pl', '.pm', '.rb', '.graphql', '.gql',
        '.cbl', '.cob', '.h', '.hpp'
    })
    _, ext = os.path.splitext(filename)
    return ext.lower() in program_extensions

def find_program_files(directory):
    program_files = []
    index = len(directory) + 1
    for root, _, files in os.walk(directory):
        for file in files:
            if is_program_file(file):
                full_path = os.path.join(root, file)
                with open(full_path, 'r', encoding='utf-8') as file:
                    code = file.read()
                prompt = f"请用一句话概括{file}的功能，代码: \n{code}\n，只需概括，不需解释函数、类的作用，一句话即可。请用中文回答"
                file_function = codegeex_generate(prompt)
                program_files.append((full_path[index:],file_function))
                yield program_files


def generate_tree(folder_path):
    folder_path = os.path.basename(folder_path)
    tree_str = subprocess.run(f"""tree {folder_path}""",
                              shell=True,
                              text=True,
                              check=True,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,cwd='repositry').stdout
    tree_array = tree_str.split('\n')
    new_tree_array = [file for file in tree_array if '.' not in file or is_program_file(file)]
    return '\n'.join(new_tree_array[:-2])


def generate_markdown(commentPairList):
    markdown_lines = [f"|{file}|{func}|" for file, func in commentPairList]
    return "\n".join(["|文件名|功能概括|\n|:-:|:-:|"] + markdown_lines)


def analyze_folder(folder_path):
    repoStructure = generate_tree(folder_path)
    yield repoStructure
    structureGenerator = find_program_files(folder_path)
    for structure in structureGenerator:
        repoFunction = generate_markdown(structure)
        yield repoStructure + '\n' + repoFunction

# individual code module
def generate_docstring(file):
    file = f'code/{file}'
    if is_program_file(file):
        with open(file, 'r', encoding='utf-8') as f:
            code = f.read()
        result = codestral_stream(f"{code}\n\n为代码写注释")
        for chunk in result:
            yield (f"为{file}写注释",chunk)
    else:
        yield (f"为{file}写注释", "请检查文件类型是否正确")

def optimize_code(file):
    file = f'code/{file}'
    if is_program_file(file):
        with open(file, 'r', encoding='utf-8') as f:
            code = f.read()
        result = codestral_stream(f"{code}\n\n对代码进行性能优化、可读性优化和安全性优化")
        for chunk in result:
            yield ("优化代码",chunk)
    else:
        yield ("优化代码", "请检查文件类型是否正确")
