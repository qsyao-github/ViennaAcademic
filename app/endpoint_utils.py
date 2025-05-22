from typing import AsyncGenerator
import datetime
from chat_utils.chat import ChatManager
from va_rust_utils import (
    chat_utils_attachment_processor_process_attachments as process_attachments,
)
import aiofiles

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
        "application/pdf",  # pdf
        "application/vnd.oasis.opendocument.text",  # odt
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # pptx
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
    ]
)


async def respond_stream(
    query: str,
    thread_id: str,
    chat_mode: str,
    current_user: str,
) -> AsyncGenerator[str, None]:
    if not query:
        yield ""
        return
    now_time = datetime.datetime.now().strftime("%y%m%d%H%M%S")

    # 预处理
    formatted_text = process_attachments(query, current_user)

    # 流式输出
    bot_response = ChatManager.astream_response(
        formatted_text,
        [],
        thread_id,
        chat_mode,
        now_time,
    )
    async for response_chunk in bot_response:
        yield response_chunk


async def file_stream(file_path: str) -> AsyncGenerator[bytes, None]:
    async with aiofiles.open(file_path, mode="rb") as f:
        while chunk := await f.read(1048576):
            yield chunk
