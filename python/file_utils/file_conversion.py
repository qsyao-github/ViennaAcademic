"""
文件转换模块
"""

import os
import re
import subprocess

from python.file_utils.marker_parser import pdf_to_markdown
from va_rust_utils import (
    file_utils_file_conversion_markdown_to_everything as markdown_to_everything,
)

# 由marker处理的文件类型
marker_ext = frozenset([".pdf", ".pptx", ".xlsx"])
# 清洗图片和引用
remove_image_pattern = re.compile(r"!\[.*?\]\(.*?\)\s*(?:\{.*?\}\s*)?", re.DOTALL)


def pandoc_to_markdown(
    file_basename: str, original_file_path: str, target_path: str
) -> None:
    """用pandoc转换为markdown

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
    result = subprocess.run(
        [
            "pandoc",
            "-s",
            "--link-images=false",
            "--reference-links=false",
            "-t",
            "markdown",
            original_file_path,
        ],
        check=True,
        text=True,
        capture_output=True,
    ).stdout
    result = remove_image_pattern.sub("", result)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)


def marker_parse(file_basename: str, original_file_path: str, target_path: str) -> None:
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
    result = pdf_to_markdown(original_file_path)
    output_path = os.path.join(target_path, f"{file_basename}.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)


def everything_to_markdown(original_path: str, target_path: str) -> None:
    """将任意格式转换为markdown的高级接口

    Parameters
    ----------
    original_path: str
        原文件路径
    target_path: str
        目标路径
    """
    file_name, ext = os.path.splitext(original_path)
    file_basename = os.path.basename(file_name)
    if ext in marker_ext:
        marker_parse(file_basename, original_path, target_path)
    else:
        pandoc_to_markdown(file_basename, original_path, target_path)
