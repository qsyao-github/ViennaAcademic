"""
快速解析pdf

使用pymupdf.layout和pymupdf4llm
"""

import re
from typing import Generator

import pymupdf.layout
import pymupdf4llm

LINE_BREAK_PATTERN = re.compile(r"\s*\n{2,}\s*")


def pymupdf_parse(data: bytes) -> Generator[str, None, None]:
    doc = pymupdf.open(stream=data)
    md: str = pymupdf4llm.to_markdown(doc, use_ocr=False)
    for line in re.split(LINE_BREAK_PATTERN, md):
        # picture ignored 或 picture text
        if (
            line.startswith("**==> picture [")
            and line.endswith("] intentionally omitted <==**")
        ) or (
            line.startswith("**----- Start of picture text -----**")
            and line.endswith("**----- End of picture text -----**<br>")
        ):
            continue
        yield line
