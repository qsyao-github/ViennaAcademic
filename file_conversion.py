import os
import subprocess
import re

from marker_parser import pdf_to_markdown

marker_ext = frozenset([".pdf", ".pptx", ".xlsx"])
remove_image_pattern = re.compile(r"!\[.*?\]\(.*?\)\s*(?:\{.*?\}\s*)?", re.DOTALL)
remove_citation_pattern = re.compile(r"#cite\([^)]*\)")


def pandoc_to_markdown(file_basename: str, original_file_path: str, target_path: str):
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


def pandoc_convert(
    file_basename: str, original_file_path: str, target_path: str, target_ext: str
):
    output_path = os.path.join(target_path, f"{file_basename}.{target_ext}")
    subprocess.run(
        [
            "pandoc",
            "-s",
            "--link-images=false",
            "--reference-links=false",
            "-o",
            output_path,
            original_file_path,
        ],
        check=True,
        text=True,
        capture_output=True,
    )


def marker_parse(file_basename: str, original_file_path: str, target_path: str):
    result = pdf_to_markdown(original_file_path)
    # result = remove_image_pattern.sub("", result)
    output_path = os.path.join(target_path, f"{file_basename}.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)


def everything_to_markdown(original_path: str, target_path: str):
    file_name, ext = os.path.splitext(original_path)
    file_basename = os.path.basename(file_name)
    if ext in marker_ext:
        marker_parse(file_basename, original_path, target_path)
    else:
        pandoc_to_markdown(file_basename, original_path, target_path)


def markdown_to_pdf(file_basename: str, original_path: str, target_path: str):
    typst_source = subprocess.run(
        [
            "pandoc",
            "-s",
            "--link-images=false",
            "--reference-links=false",
            "-t",
            "typst",
            original_path,
        ],
        check=True,
        text=True,
        capture_output=True,
    ).stdout
    typst_source = remove_citation_pattern.sub("", typst_source)
    typst_source = typst_source.replace(
        "font: ()",
        'font: ((name: "libertinus serif", covers: "latin-in-cjk"),"Noto Sans CJK SC")',
        1,
    )
    subprocess.run(
        [
            "/home/laowei/typst-x86_64-unknown-linux-musl/typst",
            "compile",
            "-",
            f"{target_path}/{file_basename}.pdf",
        ],
        input=typst_source,
        check=True,
        text=True,
        capture_output=True,
    )


def markdown_to_everything(original_path: str, target_path: str, target_ext: str):
    file_name, _ = os.path.splitext(original_path)
    file_basename = os.path.basename(file_name)
    if target_ext != "pdf":
        pandoc_convert(file_basename, original_path, target_path, target_ext)
    else:
        markdown_to_pdf(file_basename, original_path, target_path)
