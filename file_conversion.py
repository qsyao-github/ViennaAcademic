import os
import subprocess

from marker_parser import pdf_to_markdown

marker_ext = frozenset([".pdf", ".pptx", ".xlsx"])


def pandoc_parse(
    original_file_name: str, original_file_path: str, target_path: str, target_ext: str
):
    original_file_basename = os.path.basename(original_file_name)
    output_path = os.path.join(target_path, f"{original_file_basename}.{target_ext}")
    subprocess.run(
        ["pandoc", "-t", "markdown", "-s", "-o", output_path, original_file_path],
        check=True,
    )


def marker_parse(original_file_name: str, original_file_path: str, target_path: str):
    result = pdf_to_markdown(original_file_path)
    original_file_basename = os.path.basename(original_file_name)
    output_path = os.path.join(target_path, f"{original_file_basename}.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)


def everything_to_markdown(original_path: str, target_path: str):
    file_name, ext = os.path.splitext(original_path)
    if ext in marker_ext:
        marker_parse(file_name, original_path, target_path)
    else:
        pandoc_parse(file_name, original_path, target_path, "md")
