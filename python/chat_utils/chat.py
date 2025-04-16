"""
主页面聊天和解题/代码聊天后端
"""

from io import StringIO
from typing import Any, AsyncGenerator, Dict, Iterator, List, Tuple, Union

from langchain_core.messages import AIMessage, HumanMessage, RemoveMessage
from python.chat_utils.agent_backend import agent_app
from python.chat_utils.chat_backend import solve_app
from python.chat_utils.media_handler import create_image_component
from python.chat_utils.tool_formatter import format_tools
from python.web_utils.search import generate_academic_search_summary


class ChatManager:
    """主页面聊天管理"""

    @staticmethod
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
        content: List[Dict]
            消息内容
        """
        content = [{"type": "text", "text": text}]
        for f in files:
            if component := create_image_component(f):
                content.append(component)
        return content

    @staticmethod
    async def handle_generated_image(
        timestamp: str, chat_config: Dict[str, Dict[str, str]]
    ) -> None:
        """处理生成的图片并更新状态

        Parameters
        ----------
        timestamp : str
            当前时间戳，格式为%y%m%d%H%M%S，用于常规模式模型生成图片
        chat_config : Dict
            聊天配置，包含线程id。对指定线程的状态进行更新

        Notes
        ----------
        1. 对于messages，langchain实现了reducer函数，信息默认附加在上一个状态后
        2. 图片由模型工具调用生成，但将其作为HumanMessage储存，以便多模态模型推理
        """
        image_path = f"media/{timestamp}.png"
        if image_component := create_image_component(image_path):
            await agent_app.aupdate_state(
                chat_config, {"messages": HumanMessage([image_component])}
            )

    @staticmethod
    async def astream_response(
        text: str, files: List[str], thread_id: str, mode: str, timestamp: str
    ) -> AsyncGenerator[str, None]:
        """流式处理聊天响应

        Parameters
        ----------
        text: str
            聊天文本
        files: List[str]
            文件路径列表
        thread_id: str
            线程id，langgraph底层对每个线程id分别维护状态(包括messages)。选用Gradio端的聊天记录中的第一个字典的字符串形式，保证每次聊天记录分开储存。
        mode: str
            聊天模式：常规，工具，多模态，知识库，网页搜索
        timestamp: str
            当前时间戳，格式为%y%m%d%H%M%S，用于常规模式模型生成图片

        Yields
        ----------
        str
            模型返回内容->工具调用排版。因Gradio不支持增量更新，所有返回的字符串均为完整的回复
        """
        chat_config = {
            "configurable": {
                "thread_id": thread_id,
                "mode": mode,
                "now_time": timestamp,
            }
        }
        content = ChatManager.build_message_content(text, files)
        buffer = StringIO()
        async for chunk, _ in agent_app.astream(
            {"messages": [HumanMessage(content=content)]},
            config=chat_config,
            stream_mode="messages",
        ):
            buffer.write(
                chunk.content
                or chunk.additional_kwargs.get(
                    "tool_calls", [{"function": {"arguments": ""}}]
                )[0]["function"]["arguments"]
            )
            yield buffer.getvalue()

        final_response = format_tools(buffer.getvalue())
        buffer.close()
        await ChatManager.handle_generated_image(timestamp, chat_config)
        yield final_response

    @staticmethod
    async def append_search_result(
        query: str, thread_id: str
    ) -> AsyncGenerator[str, None]:
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
        await agent_app.aupdate_state(
            {"configurable": {"thread_id": thread_id}},
            {
                "messages": [
                    HumanMessage([{"type": "text", "text": f"请搜索{query}"}]),
                    AIMessage(final_result),
                ]
            },
        )
        yield final_result


class SolveManager:
    """解题/代码功能管理

    Attributes
    ----------
    LENGTH_OF_THINK_TAG: int
        len('<think>') + 1 = 8，去除模型回复的<think>标签
    TAG_MODEL_INDEXES: frozenset[int]
        储存使用<think>标签的模型索引。目前0号qwq-32b，1号deepseek-r1-671b都是此类模型。
    """

    LENGTH_OF_THINK_TAG = 8
    TAG_MODEL_INDEXES = frozenset({0, 1})

    @classmethod
    def split_final_response(cls, content: str) -> Tuple[str, str]:
        """分割思考和回答部分，去除<think>标签

        Parameters
        ----------
        content: str
            模型返回内容

        Returns
        ----------
        Tuple[str, str]
            思考部分，回答部分。分开渲染，其中思考部分放入metadata框中。
        """
        split_result = content.rsplit("</think>", 1)
        if len(split_result) > 1:
            return split_result[0][cls.LENGTH_OF_THINK_TAG:].strip(), split_result[-1]
        return "", content

    @classmethod
    async def handle_tag_model(
        cls,
        chat_config: dict,
        content_buffer: StringIO,
        answer: Iterator[Union[dict[str, Any], Any]],
    ) -> AsyncGenerator[Tuple[str, str], None]:
        """处理使用<think>标签的模型

        涉及分割思考和回答部分，去除<think>标签，以及去除状态中的思考部分

        Parameters
        ----------
        chat_config: dict
            线程id，langgraph底层对每个线程id分别维护状态(包括messages)。选用Gradio端的聊天记录中的第一个字典的字符串形式，保证每次聊天记录分开储存。
        content_buffer: StringIO
            储存模型返回字符串。因Gradio不支持增量更新，所有返回的字符串均为完整的回复
        answer: Iterator[Union[dict[str, Any], Any]]
            模型返回内容

        Yields
        ----------
        Generator[Tuple[str, str], None, None]
            思考部分，回答部分。分开渲染，其中思考部分放入metadata框中。
        """
        async for chunk, _ in answer:
            content_buffer.write(chunk.content)
            yield "", content_buffer.getvalue()
        full_response = content_buffer.getvalue()
        final_reasoning, final_answer = cls.split_final_response(full_response)
        messages = (await solve_app.aget_state(chat_config)).values["messages"]
        await solve_app.aupdate_state(
            chat_config, {"messages": RemoveMessage(id=messages[-1].id)}
        )
        await solve_app.aupdate_state(
            chat_config, {"messages": AIMessage(content=final_answer)}
        )
        yield final_reasoning, final_answer

    @classmethod
    async def handle_reasoning_model(
        cls,
        content_buffer: StringIO,
        answer: Iterator[Union[dict[str, Any], Any]],
    ) -> AsyncGenerator[Tuple[str, str], None]:
        """处理使用标准的reasoning_content的模型

        Parameters
        ----------
        content_buffer: StringIO
            储存模型返回字符串。因Gradio不支持增量更新，所有返回的字符串均为完整的回复
        answer: Iterator[Union[dict[str, Any], Any]]
            模型返回内容

        Yields
        ----------
        Generator[Tuple[str, str], None, None]
            思考部分，回答部分。分开渲染，其中思考部分放入metadata框中。
        """
        reasoning_buffer = StringIO()
        async for chunk, _ in answer:
            reasoning_buffer.write(chunk.additional_kwargs.get("reasoning_content", ""))
            content_buffer.write(chunk.content)
            yield reasoning_buffer.getvalue(), content_buffer.getvalue()
        reasoning_buffer.close()

    @classmethod
    async def astream_response(
        cls, text: str, thread_id: str, model_num: int
    ) -> AsyncGenerator[Tuple[str, str], None]:
        """根据用户提问，流式返回模型回答

        Parameters
        ----------
        text: str
            用户提问
        thread_id: str
            线程id，langgraph底层对每个线程id分别维护状态(包括messages)。选用Gradio端的聊天记录中的第一个字典的字符串形式，保证每次聊天记录分开储存。
        model_num: int
            模型索引

        Yields
        ----------
        Generator[Tuple[str, str], None, None]
            思考部分，回答部分。分开渲染，其中思考部分放入metadata框中。
        """
        chat_config = {"configurable": {"thread_id": thread_id, "model_num": model_num}}
        content_buffer = StringIO()
        answer = solve_app.astream(
            {"messages": [HumanMessage(text)]},
            config=chat_config,
            stream_mode="messages",
        )
        if model_num in cls.TAG_MODEL_INDEXES:
            handler = cls.handle_tag_model(chat_config, content_buffer, answer)
        else:
            handler = cls.handle_reasoning_model(content_buffer, answer)
        async for item in handler:
            yield item
        content_buffer.close()
