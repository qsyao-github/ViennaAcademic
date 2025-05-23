import glob
from typing import AsyncGenerator

from chat_utils.chat import ChatManager
from pydantic import BaseModel
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


class ModelResponseChunk(BaseModel):
    text: str
    image_urls: list[str]


async def respond_stream(
    query: str,
    image_urls: list[str],
    thread_id: str,
    chat_mode: str,
    current_user: str,
) -> AsyncGenerator[ModelResponseChunk, None]:
    if not query:
        yield None
        return

    # 预处理
    formatted_text = process_attachments(query, current_user)

    # 流式输出
    bot_response = ChatManager.astream_response(
        formatted_text,
        image_urls,
        thread_id,
        chat_mode,
        thread_id,
    )
    async for response_chunk in bot_response:
        yield ModelResponseChunk(text=response_chunk, image_urls=[])

    # 附加图片
    yield ModelResponseChunk(
        text="",
        image_urls=[f"/{path}" for path in glob.glob(f"media/{thread_id}*.png")],
    )
