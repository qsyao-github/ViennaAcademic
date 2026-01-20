"""
Vienna Academic后端服务

启动: fastapi run server.py --port 8001
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Annotated

import magic
import uvloop
from dotenv import load_dotenv
from fastapi import FastAPI, Form, UploadFile
from sse_starlette import EventSourceResponse, ServerSentEvent

load_dotenv()
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

from chat import chat_stream, delete_thread, get_history
from chat.agent import close_agent, get_agent
from chat.history_management import get_thread_ids
from chat.message_chunk_wrapper import image_chunk, text_chunk
from chat.tools import ToolName

ALLOWED_IMAGE_TYPE = frozenset(["image/jpeg", "image/png"])
mime = magic.Magic(mime=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """在服务器关闭后关闭sqlite连接"""
    await get_agent()
    yield
    await close_agent()


app = FastAPI(lifespan=lifespan)

# 聊天系统


@app.post("/chat/{thread_id}")
async def chat(
    thread_id: str,
    text: Annotated[str, Form()],
    images: list[UploadFile] = [],
    multimodal: Annotated[bool, Form()] = False,
    thinking: Annotated[bool, Form()] = False,
    tools: Annotated[frozenset[ToolName], Form()] = frozenset(),
) -> EventSourceResponse:
    """发送用户消息，LLM流式回复。

    - Args:
        - thread_id (str): 当前对话标识符。详见Notes
        - text (Annotated[str, Form()]): 用户发送的文字信息
        - images (list[UploadFile]): 用户发送的图片（若有）
        - multimodal (Annotated[bool, Form()]): 是否使用多模态模型
        - thinking (Annotated[bool, Form()]): 是否使用推理模型
        - tools (Annotated[frozenset[ToolName], Form()]): 启用的工具

    - Returns:
        - EventSourceResponse: LLM返回的SSE流，具体格式见Notes

    - Notes:
        - thread_id:
            - 可理解为每个thread_id对应一个对话历史，当前用户发送的消息应接在该对话历史后
            - 后端会根据thread_id获取以前的对话历史，因此该端口只接受用户最新发送的文本、图片
            - thread_id须由前端提供，因为只有前端才知道用户正在参与哪个对话
            - 建议: thread_id可以包含用户信息、对话创建时间、对话内容概要（例如用户输入的第一句话）等信息，保证唯一性，也方便前端显示概要、后端筛选某用户的对话

        - tools:
            - 必须为下列几种字符串: ipython, general_search, academic_search
                - ipython: ipython代码执行，注意该工具可能返回图片
                - general_search: Tavily上网搜索
                - academic_search: Semantic Scholar论文搜索
            - 工具调用的SSE格式见下文SSE data格式部分

        - SSE data格式:
            - 可以参考app/chat_samples下的测试用例
            - data是json，一定包含role和type字段
            - 如果type为text/reasoning/tool_call/tool_call_chunk，会通过content字段传输
            - 如果type为image，会通过mime_type字段传输图片类型，base64字段传输base64编码
            - role: 可能为user, assistant, tool
            - type:
                - text: 正文
                - reasoning: LLM推理内容
                - tool_call_chunk: LLM流式输出的工具调用片段，拼接起来是json
                - tool_call: LLM的完整工具调用，是用户可读的markdown
                    - tool_call_chunk全部输出后一定会发送tool_call，前端需用tool_call的markdown取代其前面的tool_call_chunk拼接的json
                    - tool_call也可单独出现
                - image: 图片
    """
    messages = [
        image_chunk(data, mime_type)
        for image in images
        if (mime_type := mime.from_buffer((data := await image.read())))
        in ALLOWED_IMAGE_TYPE
    ]
    messages.append(text_chunk(text))
    event_stream = (
        ServerSentEvent(data=data)
        async for data in chat_stream(thread_id, messages, multimodal, thinking, tools)
    )
    return EventSourceResponse(event_stream)


@app.get("/list_thread_ids")
async def list_thread_ids() -> frozenset[str]:
    """
    列出所有对话的thread_id

    - Returns:
        - frozenset[str]: 所有对话的thread_id。thread_id含义详见/chat的notes
    """
    return await get_thread_ids()


@app.get("/get_history/{thread_id}")
async def history(thread_id: str) -> EventSourceResponse:
    """
    获取thread_id对应的历史对话

    - Args:
        - thread_id (str): 对话标识符，详见/chat的notes

    - Returns:
        - EventSourceResponse: 历史对话SSE流，详见/chat的notes

    - Notes:
        - 历史对话SSE流被设计为和/chat格式一致，前端或可用同一个函数统一处理
    """
    event_stream = (ServerSentEvent(data=data) async for data in get_history(thread_id))
    return EventSourceResponse(event_stream)


@app.delete("/delete_history/{thread_id}")
async def delete_history(thread_id: str):
    """
    删除某个thread_id对应的对话

    - Args:
        - thread_id (str): 对话标识符，详见/chat的notes
    """
    await delete_thread(thread_id)
