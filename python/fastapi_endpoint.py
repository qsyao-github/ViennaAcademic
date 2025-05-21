import asyncio
import datetime
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvloop
from chat_utils.agent_backend import get_agent_app, close_conn
from chat_utils.chat import ChatManager
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from va_rust_utils import (
    chat_utils_attachment_processor_process_attachments as process_attachments,
)

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_agent_app()
    print("agent app loaded")
    yield
    await close_conn()


app = FastAPI(lifespan=lifespan)


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


@app.post("/respond")
async def respond(query: str, thread_id: str, chat_mode: str, current_user: str):
    return StreamingResponse(respond_stream(query, thread_id, chat_mode, current_user))
