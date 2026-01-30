"""
封装各类文本/文件为langchain content block
"""

import base64
from typing import Optional

from .file_parsing import quick_parse

ALLOWED_IMAGE_TYPE = frozenset(("image/jpeg", "image/png"))
ALLOWED_FILE_TYPE = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "text/html": "html",
    "application/pdf": "pdf",
}


def text_chunk(text: str) -> dict[str, str]:
    """将文本打包成langchain content block"""
    return {"type": "text", "text": text}


def image_chunk(data: bytes, mime_type: str) -> dict[str, str]:
    """根据图片二进制和类型生成langchain content block"""
    encoded_base64 = base64.b64encode(data).decode("utf-8")
    return {"type": "image", "mime_type": mime_type, "base64": encoded_base64}


def media_chunk(data: bytes, mime_type: str) -> Optional[dict[str, str]]:
    """将前端上传的已支持的文件转换为文本content block/图片content block"""
    if mime_type in ALLOWED_IMAGE_TYPE:
        return image_chunk(data, mime_type)
    if mime_type in ALLOWED_FILE_TYPE:
        text = quick_parse(data, ALLOWED_FILE_TYPE[mime_type])
        if text is not None:
            return text_chunk(text)
    if mime_type.startswith("text"):
        return text_chunk(data.decode("utf-8"))
