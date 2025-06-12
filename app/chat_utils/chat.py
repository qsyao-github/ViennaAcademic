"""
聊天后端
"""

import glob
from typing import AsyncGenerator, Dict, List, Union

from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage, ToolMessage
from va_rust_utils import create_image_component, process_attachments
from web_utils.search import generate_academic_search_summary

from .agent_backend import ENABLE_REASONING, get_agent_app


def build_message_content(
    text: str, files: List[str]
) -> List[Dict[str, Union[str, Dict[str, str]]]]:
    """构建消息内容

    Parameters
    ----------
    text : str
        聊天文本
    files : List[str]
        文件路径列表

    Returns
    ----------
    List[Dict]
        消息内容
    """
    return [component for f in files if (component := create_image_component(f))] + [
        {"type": "text", "text": text}
    ]


async def handle_generated_image(
    chat_config: Dict[str, Dict[str, str]], image_files_set: set
) -> None:
    """处理生成的图片并更新状态

    Parameters
    ----------
    chat_config : Dict
        聊天配置，包含线程id。对指定线程的状态进行更新
    image_files_set : set
        需要处理的媒体文件路径

    Notes
    ----------
    1. 对于messages，langchain实现了reducer函数，信息默认附加在上一个状态后
    2. 图片由模型工具调用生成，但将其作为HumanMessage储存，以便多模态模型推理
    """
    """ for f in image_files_set:
        if image_component := create_image_component(f):
            await (await get_agent_app()).aupdate_state(
                chat_config, {"messages": HumanMessage([image_component])}
            ) """
    if image_files_set:
        await (await get_agent_app()).aupdate_state(
            chat_config,
            {
                "messages": HumanMessage(
                    [
                        image_component
                        for f in image_files_set
                        if (image_component := create_image_component(f))
                    ]
                )
            },
        )


async def process_reasoning(chat_config: Dict[str, Dict[str, str]]) -> None:
    """
    对于返回<think></think>的模型，删去其思考过程。正常模型不变
    """
    if not (chat_config["configurable"]["model_type"] & ENABLE_REASONING):
        return
    messages = (await (await get_agent_app()).aget_state(chat_config)).values[
        "messages"
    ]
    last_message: str = messages[-1].content
    if "<think>" in last_message:
        last_message = last_message[last_message.rfind("</think>") + 9 :]
        await (await get_agent_app()).aupdate_state(
            chat_config,
            {
                "messages": [
                    RemoveMessage(id=messages[-1].id),
                    AIMessage(content=last_message),
                ]
            },
        )


async def astream_response(
    text: str,
    images: List[str],
    documents: List[str],
    thread_id: str,
    model: str,
    model_type_code: int,
) -> AsyncGenerator[str, None]:
    """流式处理聊天响应

    Parameters
    ----------
    text: str
        聊天文本
    images: List[str]
        图片url列表
    documents: List[str]
        引用文本url列表
    thread_id: str
        线程id，langgraph底层对每个线程id分别维护状态(包括messages)
    model: str
        模型名称
    model_type_code: int
        模型类型位掩码

    Yields
    ----------
    str
        模型返回内容，可能为chat(一般文本), tool_call(工具调用文本), tool_result(工具调用结果), reasoning(推理部分)。流式返回增量部分
    """
    # 构建配置
    chat_config = {
        "configurable": {
            "thread_id": thread_id,
            "model": model,
            "model_type": model_type_code,
        }
    }
    # 预处理：处理文本和图片
    content = build_message_content(process_attachments(text, documents), images)
    old_file_set = set(glob.iglob(f"media/{thread_id}/*.png"))
    # 维护是否推理，是否是第一个content块，前一个输出的模式三种状态
    in_reasoning = False
    start_chunks = True
    # 初始化content缓冲区
    content_buffer: str = ""
    # 接收模型回复+处理
    async for chunk, _ in (await get_agent_app()).astream(
        {"messages": [HumanMessage(content=content)]},
        config=chat_config,
        stream_mode="messages",
    ):
        # 流式输出，空内容不输出。<think> tag特殊处理
        if content := chunk.content:
            # 处理上次工具调用
            if isinstance(chunk, ToolMessage):
                # 新生成的图像
                new_file_set = set(glob.iglob(f"media/{thread_id}/*.png"))
                generated_images = new_file_set - old_file_set
                if generated_images:
                    yield f"""event: image_output\ndata: {{content: {list(generated_images)}}}\n\n"""
                    old_file_set = new_file_set
                # 工具调用结果
                yield f"""event: tool_result\ndata: {{content: "```\n{content}\n```\n\n"}}\n\n"""
                continue
            start_chunks = True
            # 跳过执行过程中模型生成的图片信息。该图片信息类型为List
            if not isinstance(content, str):
                continue
            # 通过buffer处理content中的<think> tag
            content_buffer += content
            # 固定buffer长度为11，这是最小长度，减少find的开销
            if (current_length := len(content_buffer)) > 11:
                # 未开始推理
                if not in_reasoning:
                    # 有推理开始标志，think仅出现在回复流开头，不是开头可直接跳过startswith判断
                    if start_chunks and content_buffer.startswith("<think>\n"):
                        # 更新状态：正在推理/非开头
                        in_reasoning = True
                        start_chunks = False
                        # 去除<think> tag
                        content_buffer = content_buffer[8:]
                    else:
                        # yield buffer前面的一部分并去除，保持buffer长度为11
                        border = current_length - 11
                        yield f"""event: chat\ndata: {{content: "{content_buffer[:border]}"}}\n\n"""
                        content_buffer = content_buffer[border:]
                # 已开始推理
                else:
                    # 有推理结束标志
                    if (index := content_buffer.rfind("\n</think>\n")) != -1:
                        # 更新状态：未开始推理
                        in_reasoning = False
                        # 完整输出</think> tag前内容，去除</think> tag
                        yield f"""event: reasoning\ndata: {{content: "{content_buffer[:index]}"}}\n\n"""
                        content_buffer = content_buffer[index + 10 :]
                    else:
                        # yield buffer前面的一部分并去除，保持buffer长度为11
                        border = current_length - 11
                        yield f"""event: reasoning\ndata: {{content: "{content_buffer[:border]}"}}\n\n"""
                        content_buffer = content_buffer[border:]
        elif content := chunk.additional_kwargs.get("tool_calls", ""):
            # yield content_buffer中未输出的内容，状态复位
            if content_buffer:
                yield f"""event: chat\ndata: {{content: "{content_buffer}"}}\n\n"""
            content_buffer = ""
            start_chunks = True
            in_reasoning = False
            yield f"""event: tool_call\ndata: {{content: "{content[0]["function"]["arguments"]}"}}\n\n"""
        elif content := chunk.additional_kwargs.get("reasoning_content", ""):
            # yield content_buffer中未输出的内容，状态复位
            if content_buffer:
                yield f"""event: chat\ndata: {{content: "{content_buffer}"}}\n\n"""
            content_buffer = ""
            start_chunks = True
            in_reasoning = False
            yield f"""event: reasoning\ndata: {{content: "{content}"}}\n\n"""
    # yield content_buffer中未输出的内容，发送finish信息
    if content_buffer:
        yield f"""event: chat\ndata: {{content: "{content_buffer}"}}\n\n"""
    # 推理模型特殊处理：移除<think></think>内容
    await process_reasoning(chat_config)


async def append_search_result(query: str, thread_id: str) -> AsyncGenerator[str, None]:
    """处理学术搜索结果

    将模型生成的概述和参考文献返回Gradio，在完成恢复后将回复并入状态中

    Parameters
    ----------
    query: str
        搜索关键词
    thread_id: str
        线程id，langgraph底层对每个线程id分别维护状态(包括messages)。选用Gradio端的聊天记录中的第一个字典的字符串形式，保证每次聊天记录分开储存。

    Yields
    ----------
    final_result: str
        模型生成概述。因Gradio不支持增量更新，所有返回的字符串均为完整的回复
    """
    final_result = ""
    search_result = generate_academic_search_summary(query)
    async for chunk_result in search_result:
        final_result = chunk_result
        yield final_result
    await (await get_agent_app()).aupdate_state(
        {"configurable": {"thread_id": thread_id}},
        {
            "messages": [
                HumanMessage([{"type": "text", "text": f"请搜索{query}"}]),
                AIMessage(final_result),
            ]
        },
    )
    yield final_result
