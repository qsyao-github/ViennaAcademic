"""
Github解析功能
"""
import os
import subprocess
from typing import Generator, List, Tuple

from langchain_core.prompts import ChatPromptTemplate
from modelclient import codestral_latest
"""程序文件后缀"""
program_extensions = frozenset(
    {
        ".vue",
        ".js",
        ".ts",
        ".html",
        ".htm",
        ".css",
        ".jsx",
        ".c",
        ".cpp",
        ".cxx",
        ".cc",
        ".java",
        ".py",
        ".go",
        ".php",
        ".rs",
        ".sql",
        ".m",
        ".mm",
        ".kt",
        ".swift",
        ".pl",
        ".pm",
        ".rb",
        ".graphql",
        ".gql",
        ".cbl",
        ".cob",
        ".h",
        ".hpp",
    }
)

explain_code_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "请用一句话概括{file}的功能，只需概括，不需解释函数、类的作用，一句话即可。请用中文回答",
        ),
        ("user", "{code}"),
    ]
)


def is_program_file(filename: str) -> bool:
    """判断文件是否为程序文件
    
    Parameters
    ----------
    filename : str
        文件名
    
    Returns
    ----------
    bool
        是否为程序文件
    """
    _, ext = os.path.splitext(filename)
    return ext.lower() in program_extensions


def find_program_files(directory: str) -> Generator[List[Tuple[str, str]], None, None]:
    """查找目录下的程序文件并概括功能

    概括目前使用codestral-latest
    
    Parameters
    ----------
    directory : str
        目录路径
    
    Yields
    ----------
    List[Tuple[str, str]]
        程序文件路径和功能概括。由于Gradio不支持增量更新，每次都会返回所有文件的功能概括
    """
    program_files = []
    index = len(directory) + 1
    for root, _, files in os.walk(directory):
        for file in files:
            if is_program_file(file):
                full_path = os.path.join(root, file)
                with open(full_path, "r", encoding="utf-8") as file:
                    code = file.read()
                prompt = explain_code_template.invoke({"file": file, "code": code})
                file_function = codestral_latest.invoke(prompt).content
                program_files.append((full_path[index:], file_function))
                yield program_files


def generate_tree(folder_path: str) -> str:
    """生成目录树
    
    Parameters
    ----------
    folder_path : str
        目录路径
    
    Returns
    ----------
    str
        目录树
    """
    tree_str = subprocess.run(
        f"tree {folder_path}",
        shell=True,
        text=True,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout
    tree_array = tree_str.split("\n")
    new_tree_array = [
        file for file in tree_array if "." not in file or is_program_file(file)
    ]
    return "\n".join(new_tree_array[:-2])


def generate_markdown(comment_pair_list: List[Tuple[str, str]]) -> str:
    """生成Markdown表格
    
    整理文件名和功能概括，生成markdown表格

    Parameters
    ----------
    comment_pair_list : List[Tuple[str, str]]
        文件名和功能概括的列表，由find_program_files生成
    
    Returns
    ----------
    str
        Markdown表格
    """
    markdown_lines = [f"|{file}|{func}|" for file, func in comment_pair_list]
    return "\n".join(["|文件名|功能概括|\n|:-:|:-:|"] + markdown_lines)


def analyze_folder(folder_path: str) -> Generator[str, None, None]:
    """分析Github仓库
    
    包括目录树和功能概括Markdown表格。

    Parameters
    ----------
    folder_path : str
        仓库路径
    
    Yields
    ----------
    str
        目录树和Markdown表格。因Gradio不支持增量更新，每次都会返回所有文件的功能概括。目录树生成较快，生成后直接返回一次
    """
    repo_structure = generate_tree(folder_path)
    yield repo_structure
    for structure in find_program_files(folder_path):
        repo_function = generate_markdown(structure)
        yield repo_structure + "\n" + repo_function
