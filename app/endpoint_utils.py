from typing import AsyncGenerator

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


async def respond_stream(
    query: str,
    thread_id: str,
    chat_mode: str,
    current_user: str,
) -> AsyncGenerator[str, None]:
    if not query:
        yield ""
        return

    # 预处理
    formatted_text = process_attachments(query, current_user)

    # 流式输出
    bot_response = ChatManager.astream_response(
        formatted_text,
        [],
        thread_id,
        chat_mode,
        thread_id,
    )
    async for response_chunk in bot_response:
        yield response_chunk
