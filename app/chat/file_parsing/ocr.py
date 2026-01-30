"""
高精度解析pdf

使用Deepseek OCR
"""

from typing import AsyncGenerator

import pymupdf
from langchain.messages import HumanMessage

from ..message_chunk_wrapper import image_chunk, text_chunk
from ..model import DEEPSEEK_OCR


async def ocr(data: bytes) -> AsyncGenerator[str, None]:
    batches = [
        [
            HumanMessage(
                [
                    image_chunk(page.get_pixmap(dpi=200).tobytes(), "image/png"),
                    text_chunk(
                        "<image>\n<|grounding|>Convert the document to markdown."
                    ),
                ]
            )
        ]
        for page in pymupdf.open(stream=data)
    ]
    # 去除metadata
    for page in await DEEPSEEK_OCR.abatch(batches, config={"max_concurrency": 1000}):
        content: str = page.content
        tag_removed = "\n".join(
            filter(lambda line: not line.startswith("<|ref|>"), content.splitlines())
        )
        yield tag_removed
