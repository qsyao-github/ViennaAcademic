from typing import Dict, List

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    convert_to_messages,
    merge_message_runs,
)
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.prompt_values import PromptValue
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.graph.message import BaseMessage
from langgraph.prebuilt import ToolNode, tools_condition, create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState

from execute_code import python_tool
from modelclient import pixtral_large_latest, deepseek_v3
from search import attach_web_result
from system_prompt import REGEX_TOOLCALL, WEB_SEARCH, KNOWLEDGEBASE

regex_toolcall_template = ChatPromptTemplate.from_messages(
    [("system", REGEX_TOOLCALL), MessagesPlaceholder(variable_name="messages")]
)
multimodal_template = ChatPromptTemplate.from_messages(
    [MessagesPlaceholder(variable_name="messages")]
)
web_search_template = ChatPromptTemplate.from_messages(
    [("system", WEB_SEARCH), MessagesPlaceholder(variable_name="messages")]
)
knowledgebase_template = ChatPromptTemplate.from_messages(
    [("system", KNOWLEDGEBASE), MessagesPlaceholder(variable_name="messages")]
)
select_template_from_mode = {
    "常规": regex_toolcall_template,
    "多模态": multimodal_template,
    "知识库": knowledgebase_template,
    "网页搜索": web_search_template,
}


class ChatAgentState(AgentState):
    """聊天React Agent状态"""

    mode: str
    """聊天模式：常规，多模态，知识库，网页搜索"""

    now_time: str
    """当前时间戳，格式为%y%m%d%H%M%S，用于常规模式模型生成图片"""


@tool
def websearch(query: str) -> str:
    """使用搜索引擎"""
    result = attach_web_result(query)
    return f"```\n搜索引擎前10结果：\n{result[0]}\n```\n\n参考文献\n\n{result[1]}\n\n"


@tool
def ipython(code: str) -> str:
    """使用IPython。用numpy、scipy、sympy做数值、符号计算，用matplotlib绘图"""
    return python_tool(code)


graph_builder = StateGraph(ChatAgentState)
tools = [ipython, websearch]
deepseek_v3_with_tools = deepseek_v3.bind_tools(tools)
select_model_from_mode = {
    "常规": deepseek_v3_with_tools,
    "多模态": pixtral_large_latest,
    "知识库": deepseek_v3,
    "网页搜索": deepseek_v3,
}


# 以下两个函数参考langchain_core.messages.filter_messages
def filter_tools(messages: PromptValue) -> List[BaseMessage]:
    """过滤messages中的工具调用部分，包括AIMessage的工具调用信息和ToolMessage

    Args:
        messages: 待过滤的消息列表，由ChatPromptTemplate生成

    Returns:
        过滤后的消息列表
    """
    messages = convert_to_messages(messages)
    filtered: list[BaseMessage] = []
    for message in messages:
        if isinstance(message, HumanMessage) or isinstance(message, SystemMessage):
            filtered.append(message)
        elif isinstance(message, AIMessage):
            message.additional_kwargs = {}
            message.tool_calls = []
            if message.content:
                filtered.append(message)
    return filtered


def filter_multimodal(messages: PromptValue) -> List[BaseMessage]:
    """过滤messages中的多模态部分，目前只有HumanMessage有可能出现多模态内容

    Args:
        messages: 待过滤的消息列表，由ChatPromptTemplate生成

    Returns:
        过滤后的消息列表
    """
    messages = convert_to_messages(messages)
    filtered: list[BaseMessage] = []
    for message in messages:
        if isinstance(message, HumanMessage):
            # 处理用户仅上传图片，不输入文字的情况
            filtered.append(
                HumanMessage(
                    content=[
                        chunk for chunk in message.content if chunk["type"] == "text"
                    ]
                    or [
                        {
                            "type": "text",
                            "text": "系统提示：用户没有输入任何内容，请礼貌的要求用户输入文本或使用多模态模式",
                        }
                    ]
                )
            )
        else:
            filtered.append(message)
    return filtered


def chatbot(state: ChatAgentState) -> Dict[str, List[BaseMessage]]:
    """进行一轮React Agent推理

    Args:
        state: 当前状态

    Returns:
        一轮推理后的状态。对于messages，langchain实现了reducer函数，信息默认附加在上一个状态后
    """
    mode = state["mode"]
    template = select_template_from_mode[mode]
    model = select_model_from_mode[mode]
    prompted_message = template.invoke(state)
    # 仅多模态模式的模型支持多模态信息
    if mode != "多模态":
        prompted_message = filter_multimodal(prompted_message)
    # 仅常规模式的模型支持工具信息
    if mode != "常规":
        prompted_message = filter_tools(prompted_message)
    merged = merge_message_runs(prompted_message)
    response = model.invoke(merged)
    return {"messages": [response]}


graph_builder.add_node("chatbot", chatbot)
tool_node = ToolNode(tools=tools)
graph_builder.add_node("tools", tool_node)
graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)
graph_builder.add_edge("tools", "chatbot")
graph_builder.set_entry_point("chatbot")
memory = MemorySaver()
agent_app = graph_builder.compile(checkpointer=memory)
