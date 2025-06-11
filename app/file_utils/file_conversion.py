"""
文件转换模块
"""

import os

import aiofiles
from semaphore import semaphore1
from va_rust_utils import pandoc_to_markdown

from .marker_parser import pdf_to_markdown

# 由marker处理的文件类型
marker_ext = frozenset([".pdf", ".pptx", ".xlsx"])


async def marker_parse(file_basename: str, original_file_path: str, target_path: str):
    """使用marker转换为markdown

    Parameters
    ----------
    file_basename: str
        文件名，用于指定生成文件名
    original_file_path: str
        文件路径
    target_path: str
        目标路径
    """
    output_path = os.path.join(target_path, f"{file_basename}.md")
    if os.path.exists(output_path):
        return

    # marker消耗资源极大，任意时刻只允许一个marker任务运行
    async with semaphore1:
        result = await pdf_to_markdown(original_file_path)

    # 写入
    async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
        await f.write(result)


async def everything_to_markdown(original_path: str, target_path: str):
    """将任意格式转换为markdown的高级接口

    Parameters
    ----------
    original_path: str
        原文件路径
    target_path: str
        目标路径
    """
    file_basename = os.path.basename(original_path)
    file_name, ext = os.path.splitext(file_basename)
    if ext in marker_ext:
        await marker_parse(file_name, original_path, target_path)
    else:
        pandoc_to_markdown(file_basename, original_path, target_path)
