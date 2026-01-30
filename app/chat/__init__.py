"""
为前端各端点请求准备响应数据
"""

from typing import AsyncGenerator, Optional

from langchain.messages import (
    AIMessage,
    AIMessageChunk,
    ContentBlock,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from .agent import get_agent
from .tools import format_tool_call


def content_block_adaptor(block: ContentBlock, role: str) -> Optional[dict[str, str]]:
    message_block = {"role": role, "type": block["type"]}
    match block["type"]:
        case "tool_call_chunk":
            message_block["content"] = block["args"]
        case "tool_call":
            message_block["content"] = format_tool_call(block)
        case "reasoning":
            message_block["content"] = block["reasoning"]
        case "text":
            message_block["content"] = block["text"]
        case "image":
            message_block["mime_type"] = block["mime_type"]
            message_block["base64"] = block["base64"]
        case _:
            return None
    return message_block


async def chat_stream(
    thread_id: str,
    message_chunks: list[dict[str, str]],
    multimodal: bool,
    thinking: bool,
    tools: frozenset[str],
) -> AsyncGenerator[dict[str, str], None]:
    agent = await get_agent()
    async for stream_mode, data in agent.astream(
        {"messages": [HumanMessage(message_chunks)]},
        config={"configurable": {"thread_id": thread_id}},
        context={
            "multimodal": multimodal,
            "thinking": thinking,
            "tools": tools,
        },
        stream_mode=["messages", "updates"],
    ):
        if stream_mode == "messages":
            token, metadata = data
            role = "assistant" if isinstance(token, AIMessageChunk) else "tool"
            for block in token.content_blocks:
                if (message_block := content_block_adaptor(block, role)) is not None:
                    yield message_block
        elif stream_mode == "updates":
            for source, update in data.items():
                if source == "model":
                    message = update["messages"][-1]
                    for tool_call in message.tool_calls:
                        yield {
                            "role": "assistant",
                            "type": "tool_call",
                            "content": f"{format_tool_call(tool_call)}",
                        }


async def get_history(thread_id: str) -> AsyncGenerator[dict[str, str], None]:
    agent = await get_agent()
    history = await agent.aget_state({"configurable": {"thread_id": thread_id}})
    for message in history.values.get("messages", []):
        role = None
        if isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, AIMessage):
            role = "assistant"
        elif isinstance(message, SystemMessage):
            role = "system"
        elif isinstance(message, ToolMessage):
            role = "tool"
        for block in message.content_blocks:
            if (message_block := content_block_adaptor(block, role)) is not None:
                yield message_block


async def delete_thread(thread_id: str):
    agent = await get_agent()
    await agent.checkpointer.adelete_thread(thread_id)
