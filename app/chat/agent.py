"""
聊天agent
"""

from typing import Callable

from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelRequest,
    ModelResponse,
    wrap_model_call,
    wrap_tool_call,
)
from langchain.messages import AnyMessage, HumanMessage, ToolMessage
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from .history_management import close_sqlite_connection, get_sqlite_connection
from .model import (
    DEEPSEEK_V3_2_NO_REASONING,
    DEEPSEEK_V3_2_REASONING,
    QWEN3_VL_235B_A22B_INSTRUCT,
    QWEN3_VL_235B_A22B_THINKING,
)
from .tools import get_tools

# 纯文本type
TEXT_TYPE = frozenset(("text", "reasoning", "tool_call", "tool_call_chunk"))
agent = None


def model_selector(multimodal: bool, thinking: bool) -> BaseChatModel:
    if not multimodal:
        return DEEPSEEK_V3_2_REASONING if thinking else DEEPSEEK_V3_2_NO_REASONING
    return QWEN3_VL_235B_A22B_THINKING if thinking else QWEN3_VL_235B_A22B_INSTRUCT


def multimodal_filter(messages: list[AnyMessage], multimodal: bool) -> list[AnyMessage]:
    """若使用非多模态模型，将各消息中的多模态部分过滤"""
    # 多模态模型
    if multimodal:
        return messages
    # 非多模态模型
    new_messages = []
    for message in messages:
        # 仅保留纯文本
        content = [
            block
            for block in message.content_blocks
            if isinstance(block, str) or block["type"] in TEXT_TYPE
        ]
        if content != []:
            message.content = content
            new_messages.append(message)
    return new_messages


@wrap_model_call
async def prepare_model_and_messages(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    """按需过滤多模态信息、选择模型、绑定选定工具"""
    multimodal = request.runtime.context["multimodal"]
    thinking = request.runtime.context["thinking"]
    enabled_tools = request.runtime.context["tools"]
    request = request.override(
        messages=multimodal_filter(request.messages, multimodal),
        model=model_selector(multimodal, thinking),
        tools=[tool for tool in request.tools if tool.name in enabled_tools],
    )
    return await handler(request)


@wrap_tool_call
async def handle_multimodal_tool(
    request: ToolCallRequest,
    handler: Callable[[ToolCallRequest], ToolMessage | Command],
) -> ToolMessage | Command:
    """将工具调用返回的图片改为用户发出（否则VLM无法看到）"""
    # 原始工具调用
    result: ToolMessage | Command = await handler(request)
    if isinstance(result, Command):
        return result

    content = result.content_blocks
    # 分离文本信息和图片信息
    text_content = [
        block
        for block in content
        if isinstance(block, str) or block["type"] in TEXT_TYPE
    ]
    image_content = [block for block in content if block["type"] == "image"]
    # 无图片
    if image_content == []:
        return result
    # 工具调用只保留纯文本，图片信息改为使用HumanMessage
    result.content = text_content
    return Command(
        update={
            "messages": [
                result,
                HumanMessage(content=image_content),
            ]
        }
    )


async def get_agent():
    """在异步环境获取agent，自动初始化"""
    global agent
    if agent is None:
        # 初始化数据库、中间件、工具
        tools = await get_tools()
        checkpointer = AsyncSqliteSaver(await get_sqlite_connection())
        await checkpointer.setup()
        agent = create_agent(
            DEEPSEEK_V3_2_NO_REASONING,
            checkpointer=checkpointer,
            middleware=[prepare_model_and_messages, handle_multimodal_tool],
            tools=tools,
        )
    return agent


async def close_agent():
    """关闭agent，关闭sqlite连接"""
    await close_sqlite_connection()
