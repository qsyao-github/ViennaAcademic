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


def process_directories(
    dirs: List[str], root_dir: str, mermaid_lines: List[str]
) -> None:
    """处理目录过滤和mermaid节点添加

    过滤.git

    Parameters
    ----------
    dirs: List[str]
        目录列表
    root_dir: str
        当前目录名
    mermaid_lines: List[str]
        mermaid节点列表
    """
    dirs[:] = [d for d in dirs if d != ".git"]  # 原地修改过滤.git目录
    for dir_name in dirs:
        mermaid_lines.append(f"    {root_dir} --> {dir_name}")


def process_single_file(
    file: str, root: str, root_dir: str, mermaid_lines: List[str], tasks: List[str]
) -> None:
    """处理单个文件的任务创建

    Parameters
    ----------
    file: str
        文件名
    root: str
        当前目录
    root_dir: str
        当前目录名
    mermaid_lines: List[str]
        mermaid节点列表
    tasks: List[str]
        任务列表
    """
    if not is_program_file(file):
        return

    full_path = os.path.join(root, file)
    task = asyncio.create_task(process_file(full_path, file))
    tasks.append(task)
    mermaid_lines.append(f"    {root_dir} --> {file}")


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
        mermaid字符串，程序文件路径和功能概括。由于Gradio不支持增量更新，每次都会返回所有文件的功能概括"""
    program_files = []
    tasks = []
    mermaid_lines = []

    # 第一阶段：遍历目录构建结构
    for root, dirs, files in os.walk(directory):
        root_dir = os.path.basename(root)
        process_directories(dirs, root_dir, mermaid_lines)
        for file in files:
            process_single_file(file, root, root_dir, mermaid_lines, tasks)

    # 生成初始mermaid图
    mermaid_result = f'```mermaid\ngraph LR\n{"\n".join(mermaid_lines)}\n```'
    yield mermaid_result, program_files

    # 第二阶段：异步处理任务
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

    包括目录树和功能概括Markdown表格，最后排序

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
        structure = structure
        final_function = function
        repo_function = generate_markdown(final_function)
        yield f"{structure}\n{repo_function}"
    final_function = sorted(final_function)
    repo_function = generate_markdown(final_function)
    yield f"{structure}\n{repo_function}"
