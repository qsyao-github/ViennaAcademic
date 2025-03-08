import base64
import os
import re
from io import StringIO
from typing import Dict, Generator, List, Union, Optional, Tuple
from langchain_core.messages import HumanMessage, AIMessage
from chat_backend import chat_app, solve_app
from execute_code import execute_code
from paper import attach
from perplexica import execute_search


class ContentProcessor:
    """处理内容相关的正则表达式模式"""

    # 修正后的行内公式正则表达式，正确转义反斜杠和括号
    FORMULA_INLINE_PATTERN = re.compile(r"\\\((.*?)\\\)", re.DOTALL)
    FORMULA_BLOCK_PATTERN = re.compile(r"\\\[(.*?)\\\]", re.DOTALL)
    FORMULA_CLEAN_PATTERN = re.compile(r"\$\$\s*(.*?)\s*\$\$", re.DOTALL)
    XML_TAG_PATTERN = re.compile(r"<(\w+)>(.*?)</\1>", re.DOTALL)
    ATTACH_PATTERN = re.compile(r"#attach\{([^}]+)\}")

    @staticmethod
    def format_formula(text: str) -> str:
        """统一格式化各种LaTeX公式表示形式"""
        # 处理行内公式：使用正确的捕获组引用\1
        text = ContentProcessor.FORMULA_INLINE_PATTERN.sub(r"$\1$", text)
        # 处理行间公式
        text = ContentProcessor.FORMULA_BLOCK_PATTERN.sub(r"$$\1$$", text)
        # 标准化现有公式格式
        return ContentProcessor.FORMULA_CLEAN_PATTERN.sub(r"$$\1$$", text)

    @staticmethod
    def process_attachments(text: str, current_dir: str) -> str:
        """处理附件标记替换"""

        def replace_attach(match: re.Match) -> str:
            return attach(match.group(1), current_dir)

        return ContentProcessor.ATTACH_PATTERN.sub(replace_attach, text)


class ToolExecutor:
    """工具调用执行器"""

    TOOLS = {"python": execute_code}

    @classmethod
    def execute_tools(cls, text: str) -> str:
        """执行文本中的工具调用"""

        def replace_tag(match: re.Match) -> str:
            tag, param = match.groups()
            param = param.strip()
            if not param or tag not in cls.TOOLS:
                return match.group(0)
            return cls.TOOLS[tag](param)

        return ContentProcessor.XML_TAG_PATTERN.sub(replace_tag, text)


class MediaHandler:
    """多媒体内容处理器"""

    @staticmethod
    def encode_image(image_path: str) -> str:
        """Base64编码图像文件"""
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except FileNotFoundError:
            return ""

    @staticmethod
    def create_image_component(image_path: str) -> Optional[Dict]:
        """创建图像消息组件"""
        encoded = MediaHandler.encode_image(image_path)
        if not encoded:
            return None
        return {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{encoded}", "detail": "auto"},
        }


class ChatManager:
    """聊天会话管理类"""

    @staticmethod
    def build_message_content(text: str, files: List[str]) -> List[Dict]:
        """构建消息内容结构"""
        content = [{"type": "text", "text": text}]
        for f in files:
            if component := MediaHandler.create_image_component(f):
                content.append(component)
        return content

    @staticmethod
    def handle_generated_image(timestamp: str, chat_config: Dict) -> None:
        """处理生成的图片并更新会话状态"""
        image_path = f"{timestamp}.png"
        if os.path.exists(image_path):
            image_component = MediaHandler.create_image_component(image_path)
            if image_component:
                chat_app.update_state(
                    chat_config, {"messages": HumanMessage([image_component])}
                )

    @staticmethod
    def stream_response(
        text: str, files: List[str], thread_id: str, mode: str, timestamp: str
    ) -> Generator[str, None, None]:
        """流式处理聊天响应"""
        chat_config = {"configurable": {"thread_id": thread_id}}
        content = ChatManager.build_message_content(text, files)
        buffer = StringIO()

        for chunk, _ in chat_app.stream(
            {
                "messages": [HumanMessage(content=content)],
                "mode": mode,
                "now_time": timestamp,
            },
            config=chat_config,
            stream_mode="messages",
        ):
            buffer.write(chunk.content)
            yield buffer.getvalue()

        final_response = ToolExecutor.execute_tools(buffer.getvalue())
        final_response = ContentProcessor.format_formula(final_response)
        state_before_answer = list(chat_app.get_state_history(chat_config))[-2]
        chat_app.update_state(
            state_before_answer.config, {"messages": [AIMessage(final_response)]}
        )
        ChatManager.handle_generated_image(timestamp, chat_config)
        yield final_response

    @staticmethod
    def append_search_result(query: str, focus_mode: str, thread_id: str) -> str:
        """追加搜索结果到消息"""
        search_result = execute_search(query, focus_mode)
        chat_app.update_state(
            {"configurable": {"thread_id": thread_id}},
            {"messages": [HumanMessage(f"请搜索{query}"), AIMessage(search_result)]},
        )
        return search_result


class SolveManager:
    @staticmethod
    def stream_response(
        text: str, thread_id: str, distill: int
    ) -> Generator[Tuple[str, str], None, None]:
        chat_config = {"configurable": {"thread_id": thread_id}}
        content_buffer = StringIO()
        answer = solve_app.stream(
            {"messages": [HumanMessage(text)], "distill": distill},
            config=chat_config,
            stream_mode="messages",
        )
        if distill == 0:
            temp_string = ""
            for _ in range(8):
                chunk, _ = next(answer)
                temp_string += chunk.content
            temp_string = temp_string[8:]
            content_buffer.write(temp_string)
            for chunk, _ in answer:
                content_buffer.write(chunk.content)
                yield "", content_buffer.getvalue()
            final_response = ContentProcessor.format_formula(
                content_buffer.getvalue()
            ).rsplit(r"</think>", 1)
            state_before_answer = list(solve_app.get_state_history(chat_config))[-2]
            solve_app.update_state(
                state_before_answer.config, {"messages": [AIMessage(final_response[1])]}
            )
            yield tuple(final_response)
        elif distill == 1:
            reasoning_buffer = StringIO()
            for chunk, _ in answer:
                reasoning_buffer.write(
                    chunk.additional_kwargs.get("reasoning_content", "")
                )
                content_buffer.write(chunk.content)
                yield reasoning_buffer.getvalue(), content_buffer.getvalue()
            yield ContentProcessor.format_formula(
                reasoning_buffer.getvalue()
            ), f"{ContentProcessor.format_formula(content_buffer.getvalue())}\n$$ $$"
