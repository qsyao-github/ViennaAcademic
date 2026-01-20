import base64


def text_chunk(text: str) -> dict[str, str]:
    """将文本打包成langchain content block"""
    return {"type": "text", "text": text}


def image_chunk(data: bytes, mime_type: str) -> dict[str, str]:
    """根据图片二进制和类型生成langchain content block"""
    encoded_base64 = base64.b64encode(data).decode("utf-8")
    return {"type": "image", "mime_type": mime_type, "base64": encoded_base64}
