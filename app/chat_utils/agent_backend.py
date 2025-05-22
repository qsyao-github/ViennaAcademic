"""
React Agent后端，处理ViennaAcademic中的主页面聊天部分
"""
from typing import Dict, List

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
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import tool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.prebuilt.chat_agent_executor import AgentState
from llm_utils.execute_code import python_tool
from llm_utils.modelclient import deepseek_v3, mistral_small_latest
from llm_utils.system_prompt import KNOWLEDGEBASE, REGEX_TOOLCALL, WEB_SEARCH
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from web_utils.search import attach_web_result

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
async def websearch(query: str) -> str:
    """使用搜索引擎"""
    result = await attach_web_result(query)
    return f"```\n搜索引擎前10结果：\n{result[0]}\n```\n\n参考文献\n\n{result[1]}\n\n"


@tool
def ipython(code: str) -> str:
    """使用IPython。用!执行命令，用numpy, scipy, sympy做数值/符号计算，pandas处理数据，matplotlib绘图"""
    return python_tool(code)


graph_builder = StateGraph(AgentState)
tools = [ipython, websearch]
deepseek_v3_with_tools = deepseek_v3.bind_tools(tools)
select_model_from_mode = {
    "常规": deepseek_v3,
    "工具": deepseek_v3_with_tools,
    "多模态": mistral_small_latest,
    "知识库": deepseek_v3,
    "网页搜索": deepseek_v3,
}

# 没有文本情况下的默认提示
NO_TEXT_FALLBACK = [
    {
        "type": "text",
        "text": "系统提示：用户没有输入任何内容，请要求用户输入文本或使用多模态模式",
    }
]


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


def _filter_multimodal_human_message(
    content: List[str | Dict[str, str]],
) -> List[str | Dict[str, str]]:
    """过滤HumanMessage中的多模态部分

    当过滤后没有文本部分，则返回一个默认提示

    Parameters
    ----------
    content: List[str | Dict[str, str]]
        待过滤的内容

    Returns
    ----------
    List[str | Dict[str, str]]
        过滤后的内容
    """
    return [chunk for chunk in content if chunk["type"] == "text"] or NO_TEXT_FALLBACK


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
    return [
        (
            HumanMessage(content=_filter_multimodal_human_message(message.content))
            if isinstance(message, HumanMessage)
            else message
        )
        for message in messages
    ]


async def chatbot(
    state: AgentState, config: RunnableConfig
) -> Dict[str, List[BaseMessage]]:
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
    prompted_message = await template.ainvoke(
        {"messages": state["messages"], "now_time": config["configurable"]["now_time"]}
    )
    # 仅多模态模式的模型支持多模态信息
    if mode != "多模态":
        prompted_message = filter_multimodal(prompted_message)
    # 仅工具模式的模型支持工具信息
    if mode != "工具":
        prompted_message = filter_tools(prompted_message)
    merged = merge_message_runs(prompted_message)
    response = await model.ainvoke(merged)
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

DB_URI = "postgresql://vienna_academic:vienna_academic@postgres:5432/vadb"
agent_app = None
conn = None

async def get_agent_app():
    global agent_app, conn
    if agent_app is None:
        conn = await AsyncConnection.connect(
            DB_URI, autocommit=True, prepare_threshold=0, row_factory=dict_row
        )
        postgres_checkpointer = AsyncPostgresSaver(conn=conn)
        await postgres_checkpointer.setup()
        agent_app = graph_builder.compile(checkpointer=postgres_checkpointer)
        print("agent_app started")
    return agent_app


async def close_conn():
    global conn
    conn.__aexit__()
    print("agent_app stopped")