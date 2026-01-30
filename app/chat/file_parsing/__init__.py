"""
不同精度/成本的文件解析（转markdown）

- quick_parse: pymupdf / pandoc
"""

from typing import Optional

from .basic_pdf import pymupdf_parse
from .pandoc import PANDOC_FORMAT, pandoc_parse


def quick_parse(data: bytes, format: str) -> Optional[str]:
    """临时文件解析。低成本，不追求精度"""
    if format == "pdf":
        return "\n\n".join(pymupdf_parse(data))
    elif format in PANDOC_FORMAT:
        return pandoc_parse(data, format)
