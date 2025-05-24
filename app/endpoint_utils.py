import glob
from datetime import datetime
from typing import AsyncGenerator, TypedDict

import orjson
from chat_utils.chat import ChatManager
from va_rust_utils import (
    chat_utils_attachment_processor_process_attachments as process_attachments,
)

ALLOWED_IMAGE_TYPE = frozenset(["image/jpeg", "image/png"])
ALLOWED_PAPER_TYPE = frozenset(
    [
        "text/plain",  # plain text
        "text/html",  # html
        "text/xml",  # xml
        "text/csv",  # csv
        "application/epub+zip",  # epub
        "application/json",  # json
        "application/rtf",  # rtf
        "application/vnd.oasis.opendocument.text",  # odt
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
        "application/pdf",  # pdf - marker
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # pptx - marker
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx - marker
    ]
)


class ModelResponseChunk(TypedDict):
    text: str
    image_urls: list[str]


async def respond_stream(
    query: str,
    image_urls: list[str],
    file_urls: list[str],
    thread_id: str,
    chat_mode: str,
) -> AsyncGenerator[bytes, None]:
    

    # 预处理
    formatted_text = process_attachments(query, file_urls)
    timestamp = f"{datetime.now().timestamp() * 100 % 8640000:7.0f}"
    # 流式输出
    bot_response = ChatManager.astream_response(
        formatted_text,
        image_urls,
        thread_id,
        chat_mode,
        timestamp,
    )
    async for response_chunk in bot_response:
        yield orjson.dumps(ModelResponseChunk(text=response_chunk, image_urls=[]))

    # 附加图片
    yield orjson.dumps(
        ModelResponseChunk(
            text="",
            image_urls=[f"/{path}" for path in glob.glob(f"media/{timestamp}*.png")],
        )
    )
