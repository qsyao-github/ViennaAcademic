"""
React Agent后端，处理ViennaAcademic中的主页面聊天部分
"""

from typing import Dict, List

from execute_code import python_tool
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    convert_to_messages,
    merge_message_runs,
)
from langchain_core.prompt_values import PromptValue
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_core.runnables.config import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.prebuilt.chat_agent_executor import AgentState
from modelclient import deepseek_v3, pixtral_large_latest
from search import attach_web_result
from system_prompt import KNOWLEDGEBASE, REGEX_TOOLCALL, WEB_SEARCH

empty_template = ChatPromptTemplate.from_messages(
    [MessagesPlaceholder(variable_name="messages")]
)
regex_toolcall_template = ChatPromptTemplate.from_messages(
    [("system", REGEX_TOOLCALL), MessagesPlaceholder(variable_name="messages")]
)
web_search_template = ChatPromptTemplate.from_messages(
    [("system", WEB_SEARCH), MessagesPlaceholder(variable_name="messages")]
)
knowledgebase_template = ChatPromptTemplate.from_messages(
    [("system", KNOWLEDGEBASE), MessagesPlaceholder(variable_name="messages")]
)
select_template_from_mode = {
    "常规": empty_template,
    "工具": regex_toolcall_template,
    "多模态": empty_template,
    "知识库": knowledgebase_template,
    "网页搜索": web_search_template,
}


@tool
def websearch(query: str) -> str:
    """使用搜索引擎"""
    result = attach_web_result(query)
    return f"```\n搜索引擎前10结果：\n{result[0]}\n```\n\n参考文献\n\n{result[1]}\n\n"


@tool
def ipython(code: str) -> str:
    """使用IPython。用numpy、scipy、sympy做数值、符号计算，用matplotlib绘图"""
    return python_tool(code)


graph_builder = StateGraph(AgentState)
tools = [ipython, websearch]
deepseek_v3_with_tools = deepseek_v3.bind_tools(tools)
select_model_from_mode = {
    "常规": deepseek_v3,
    "工具": deepseek_v3_with_tools,
    "多模态": pixtral_large_latest,
    "知识库": deepseek_v3,
    "网页搜索": deepseek_v3,
}


# 以下两个函数参考langchain_core.messages.filter_messages
def filter_tools(messages: PromptValue) -> List[BaseMessage]:
    """过滤messages中的工具调用

    滤去AIMessage的工具调用信息和ToolMessage

    Parameters
    ----------
    messages: PromptValue
        待过滤的消息列表，由ChatPromptTemplate生成

    Returns
    ----------
    filtered: List[BaseMessage]
        过滤后的消息列表
    """
    messages = convert_to_messages(messages)
    filtered: list[BaseMessage] = []
    for message in messages:
        if isinstance(message, (HumanMessage, SystemMessage)):
            filtered.append(message)
        elif isinstance(message, AIMessage):
            message.additional_kwargs = {}
            message.tool_calls = []
            if message.content:
                filtered.append(message)
    return filtered


def filter_multimodal(messages: PromptValue) -> List[BaseMessage]:
    """过滤messages中的多模态部分

    Parameters
    ----------
    messages: PromptValue
        待过滤的消息列表，由ChatPromptTemplate生成

    Returns
    ----------
    filtered: List[BaseMessage]
        过滤后的消息列表

    Notes
    ----------
    目前只有HumanMessage有可能出现多模态内容
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


def chatbot(state: AgentState, config: RunnableConfig) -> Dict[str, List[BaseMessage]]:
    """进行一轮React Agent推理

    Parameters
    ----------
    state: ChatAgentState
        当前状态

    Returns
    ----------
    Dict[str, List[BaseMessage]]
        一轮推理后的状态

    Notes
    ----------
    对于messages，langchain实现了reducer函数，信息默认附加在上一个状态后
    """
    mode = config["configurable"].get("mode", "常规")
    template = select_template_from_mode[mode]
    model = select_model_from_mode[mode]
    prompted_message = template.invoke(
        {"messages": state["messages"], "now_time": config["configurable"]["now_time"]}
    )
    # 仅多模态模式的模型支持多模态信息
    if mode != "多模态":
        prompted_message = filter_multimodal(prompted_message)
    # 仅工具模式的模型支持工具信息
    if mode != "工具":
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



"""使用搜索引擎"""
result = attach_web_result("Composio")
print(f"```\n搜索引擎前10结果：\n{result[0]}\n```\n\n参考文献\n\n{result[1]}\n\n")