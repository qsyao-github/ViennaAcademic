"""
Github解析功能
"""

import asyncio
import os
from typing import AsyncGenerator, List, Tuple

import aiofiles
from langchain_core.prompts import ChatPromptTemplate
from modelclient import codestral_latest
from semaphore import semaphore1

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
"""表头"""
TABLE_HEADER = "|文件名|功能概括|\n|:-:|:-:|\n"
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


async def process_file(full_path: str, basename: str) -> Tuple[str, str]:
    """异步处理单个文件

    Parameters
    ----------
    full_path: str
        文件的完整路径
    basename: str
        文件名

    Returns
    ----------
    Tuple[str, str]
        文件名和功能概括
    """
    # 异步读取文件
    async with aiofiles.open(full_path, "r", encoding="utf-8") as f:
        code = await f.read()

    # 并发执行模板生成和AI调用
    prompt_task = explain_code_template.ainvoke({"file": basename, "code": code})
    async with semaphore1:
        response = await codestral_latest.ainvoke(await prompt_task)

    # 等待结果
    file_function = response.content
    return (basename, file_function)


async def find_program_files(
    directory: str,
) -> AsyncGenerator[Tuple[str, List[Tuple[str, str]]], None]:
    """查找目录下的程序文件，生成mermaid结构图，并概括功能

    概括目前使用codestral-latest

    Parameters
    ----------
    directory : str
        目录路径

    Yields
    ----------
    Tuple[str, List[Tuple[str, str]]]
        mermaid字符串，程序文件路径和功能概括。由于Gradio不支持增量更新，每次都会返回所有文件的功能概括
    """
    program_files = []
    tasks = []
    mermaid_lines = ["graph LR"]

    for root, dirs, files in os.walk(directory):
        root_dir = os.path.basename(root)
        dirs[:] = [d for d in dirs if d != ".git"]
        for dir in dirs:
            mermaid_lines.append(f"    {root_dir} --> {dir}")
        for file in files:
            if is_program_file(file):
                full_path = os.path.join(root, file)
                tasks.append(asyncio.create_task(process_file(full_path, file)))
                mermaid_lines.append(f"    {root_dir} --> {file}")
    mermaid_result = f'```mermaid\n{"\n".join(mermaid_lines)}\n```'
    yield mermaid_result, program_files
    for task in tasks:
        rel_path, func = await task
        program_files.append((rel_path, func))
        yield mermaid_result, program_files


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
    markdown_lines = (f"|{file}|{func}|" for file, func in comment_pair_list)
    return f"{TABLE_HEADER}{"\n".join(markdown_lines)}"


async def analyze_folder(folder_path: str) -> AsyncGenerator[str, None]:
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
    async for structure, function in find_program_files(folder_path):
        repo_function = generate_markdown(function)
        yield f"{structure}\n{repo_function}"
