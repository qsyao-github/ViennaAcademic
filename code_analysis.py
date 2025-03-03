import os
import subprocess
from modelclient import codestral_latest
from langchain_core.prompts import ChatPromptTemplate
from typing import List, Tuple, Generator

program_extensions = frozenset({
    '.vue', '.js', '.ts', '.html', '.htm', '.css', '.jsx', '.c', '.cpp',
    '.cxx', '.cc', '.java', '.py', '.go', '.php', '.rs', '.sql', '.m', '.mm',
    '.kt', '.swift', '.pl', '.pm', '.rb', '.graphql', '.gql', '.cbl', '.cob',
    '.h', '.hpp'
})

explain_code_template = ChatPromptTemplate.from_messages([
    ("system", "请用一句话概括{file}的功能，只需概括，不需解释函数、类的作用，一句话即可。请用中文回答"),
    ("user", "{code}")
])


def is_program_file(filename: str) -> bool:
    _, ext = os.path.splitext(filename)
    return ext.lower() in program_extensions


def find_program_files(
        directory: str) -> Generator[List[Tuple[str, str]], None, None]:
    program_files = []
    index = len(directory) + 1
    for root, _, files in os.walk(directory):
        for file in files:
            if is_program_file(file):
                full_path = os.path.join(root, file)
                with open(full_path, 'r', encoding='utf-8') as file:
                    code = file.read()
                prompt = explain_code_template.invoke({
                    'file': file,
                    'code': code
                })
                file_function = codestral_latest.invoke(prompt).content
                program_files.append((full_path[index:], file_function))
                yield program_files


def generate_tree(folder_path):
    folder_path = os.path.basename(folder_path)
    tree_str = subprocess.run(f"tree {folder_path}",
                              shell=True,
                              text=True,
                              check=True,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              cwd='repositry').stdout
    tree_array = tree_str.split('\n')
    new_tree_array = [
        file for file in tree_array if '.' not in file or is_program_file(file)
    ]
    return '\n'.join(new_tree_array[:-2])


def generate_markdown(comment_pair_list: List[Tuple[str, str]]) -> str:
    markdown_lines = [f"|{file}|{func}|" for file, func in comment_pair_list]
    return "\n".join(["|文件名|功能概括|\n|:-:|:-:|"] + markdown_lines)


def analyze_folder(folder_path: str) -> Generator[str, None, None]:
    repo_structure = generate_tree(folder_path)
    yield repo_structure
    for structure in find_program_files(folder_path):
        repo_function = generate_markdown(structure)
        yield repo_structure + '\n' + repo_function
