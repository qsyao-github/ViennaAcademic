"""
React Agent后端，处理ViennaAcademic中的聊天部分
"""

import glob
from collections import namedtuple
from typing import Any, Dict, List, Set

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
from langchain_core.runnables import Runnable, chain
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import InjectedToolArg, tool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.prebuilt.chat_agent_executor import AgentState
from llm_utils.execute_code import python_tool
from llm_utils.modelclient import (
    deepseek_r1_671b,
    deepseek_r1_qwen3_8b,
    deepseek_v3,
    mistral_small,
    model_type,
    qwen3_8b_no_thinking,
    qwen3_8b_thinking,
    qwen3_235b_a22b_no_thinking,
    qwen3_235b_a22b_thinking,
    qwen_2_5_vl_72b,
)
from llm_utils.system_prompt import TOOLCALL
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from typing_extensions import Annotated
from va_rust_utils import create_image_component
from web_utils.search import attach_web_result

# 工具/推理/多模态位掩码
ENABLE_TOOL = model_type(True, False, False)
ENABLE_REASONING = model_type(False, True, False)
MULTIMODAL = model_type(False, False, True)


# 提示词模板
empty_template = ChatPromptTemplate.from_messages(
    [MessagesPlaceholder(variable_name="messages")]
)
toolcall_template = ChatPromptTemplate.from_messages(
    [("system", TOOLCALL), MessagesPlaceholder(variable_name="messages")]
)


# 多模态Agent状态
class MultiModalAgentState(AgentState):
    """
    除了messages，维护一个images集合，用于储存过往生成/上传的图片，防止重复
    """

    images: Set[str] = set()


graph_builder = StateGraph(MultiModalAgentState)

# 绑定工具


def tool_argument_injector(injection_config: Dict[str, Dict[str, Any]]) -> Runnable:
    """
    生成自定义参数插入函数

    Parameters
    ----------
    injection_config: Dict[str, Dict[str, Any]]
        插入配置。其键为需要插入的工具名，其值为表征插入方式的字典。该字典键为要插入的字段名，值为插入的值

    Returns
    ----------
    Runnable
        langchain Runnable对象，负责完成字段插入。与有工具的模型通过langchain管道连接。
    """

    @chain
    def injecter(ai_msg):
        for tool_call in ai_msg.tool_calls:
            if injections := injection_config.get(tool_call["name"]):
                tool_call["args"].update(injections)
        return ai_msg

    return injecter


@tool
async def websearch(query: str) -> str:
    """使用搜索引擎"""
    result = await attach_web_result(query)
    return f"```\n搜索引擎前10结果：\n{result[0]}\n```\n\n参考文献\n\n{result[1]}\n\n"


@tool
def ipython(
    code: str,
    thread_id: Annotated[str, InjectedToolArg],
) -> str:
    """使用IPython。!: 执行cmd命令，numpy, scipy, pandas: 科学计算，scikit-learn, statsmodels, patsy: 机器学习&统计，matplotlib, seaborn: 数据可视化，scikit-image: 图像处理，numba, numexpr, bottleneck: 性能加速，dask: 大数据处理，h5py, openpyxl, xlrd: 文件I/O，sympy: 符号计算"""
    return python_tool(code, thread_id)


tools = [ipython]
deepseek_v3_with_tools = deepseek_v3.bind_tools(tools)
qwen3_235b_a22b_no_thinking_with_tools = qwen3_235b_a22b_no_thinking.bind_tools(tools)
qwen3_235b_a22b_thinking_with_tools = qwen3_235b_a22b_thinking.bind_tools(tools)
qwen3_8b_no_thinking_with_tools = qwen3_8b_no_thinking.bind_tools(tools)
qwen3_8b_thinking_with_tools = qwen3_8b_thinking.bind_tools(tools)

# 模型, 位掩码(enable_tool, enable_thinking, multimodal), 模型简称
ModelInfo = namedtuple("ModelInfo", ["name", "type_code"])

models: Dict[ModelInfo, Runnable] = {
    ModelInfo(
        type_code=model_type(False, False, False), name="deepseek-v3"
    ): deepseek_v3,
    ModelInfo(
        type_code=model_type(True, False, False), name="deepseek-v3"
    ): deepseek_v3_with_tools,
    ModelInfo(
        type_code=model_type(False, True, False), name="deepseek-r1-671b"
    ): deepseek_r1_671b,
    ModelInfo(
        type_code=model_type(False, False, False), name="qwen3-235b-a22b"
    ): qwen3_235b_a22b_no_thinking,
    ModelInfo(
        type_code=model_type(True, False, False), name="qwen3-235b-a22b"
    ): qwen3_235b_a22b_no_thinking_with_tools,
    ModelInfo(
        type_code=model_type(False, True, False), name="qwen3-235b-a22b"
    ): qwen3_235b_a22b_thinking,
    ModelInfo(
        type_code=model_type(True, True, False), name="qwen3-235b-a22b"
    ): qwen3_235b_a22b_thinking_with_tools,
    ModelInfo(
        type_code=model_type(False, False, True), name="qwen2.5-vl-72b"
    ): qwen_2_5_vl_72b,
    ModelInfo(
        type_code=model_type(False, False, True), name="mistral-small"
    ): mistral_small,
    ModelInfo(
        type_code=model_type(False, False, False), name="qwen3-8b"
    ): qwen3_8b_no_thinking,
    ModelInfo(
        type_code=model_type(True, False, False), name="qwen3-8b"
    ): qwen3_8b_no_thinking_with_tools,
    ModelInfo(
        type_code=model_type(False, True, False), name="deepseek-r1-qwen3-8b"
    ): deepseek_r1_qwen3_8b,
    ModelInfo(
        type_code=model_type(True, True, False), name="qwen3-8b"
    ): qwen3_8b_thinking_with_tools,
}
available_models = [
    {
        "enable_tool": bool(code & ENABLE_TOOL),
        "enable_reasoning": bool(code & ENABLE_REASONING),
        "multimodal": bool(code & MULTIMODAL),
        "models": selected_models,
    }
    for code in range(8)
    if (selected_models := [model.name for model in models if model.type_code == code])
]


# 自定义信息过滤器，参考langchain_core.messages.filter_messages
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
) -> str:
    """过滤HumanMessage中的多模态部分

    一个HumanMessage中至多有一个文本部分，直接用next获取返回字符串。若没有文本部分，返回空字符串

    Parameters
    ----------
    content: List[str | Dict[str, str]]
        待过滤的内容

    Returns
    ----------
    str
        文本内容
    """
    return next((chunk["text"] for chunk in content if chunk["type"] == "text"), "")


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
    filtered: list[BaseMessage] = []
    messages = convert_to_messages(messages)
    for message in messages:
        if isinstance(message, HumanMessage):
            if text := _filter_multimodal_human_message(message.content):
                filtered.append(HumanMessage(content=text))
        else:
            filtered.append(message)
    return filtered


def apply_safety_filter(
    model_type: int, prompted_message: PromptValue
) -> List[BaseMessage]:
    """
    根据模型类型，过滤不能处理的信息

    Parameters
    ----------
    model_type: int
        模型类型位掩码
    prompted_message: PromptValue
        提示词

    Returns
    ----------
    prompted_message: List[BaseMessage]
        过滤后的信息列表
    """
    # 若非多模态模型，过滤多模态信息
    if not (model_type & MULTIMODAL):
        prompted_message = filter_multimodal(prompted_message)
    # 若非工具模型，过滤工具信息
    if not (model_type & ENABLE_TOOL):
        prompted_message = filter_tools(prompted_message)
    return prompted_message


# 模型调用
async def chatbot(
    state: MultiModalAgentState, config: RunnableConfig
) -> Dict[str, List[BaseMessage]]:
    """进行一轮React Agent推理

    Parameters
    ----------
    state: AgentState
        当前状态

    Returns
    ----------
    Dict[str, List[BaseMessage]]
        一轮推理后的状态

    Notes
    ----------
    对于messages，langchain实现了reducer函数，信息默认附加在上一个状态后
    """
    # 获取模型名称和位掩码
    model_type = config["configurable"].get(
        "model_type",
    )
    thread_id = config["configurable"].get("thread_id")
    # 获取模型与对应的提示词模板
    model = models[
        ModelInfo(name=config["configurable"].get("model"), type_code=model_type)
    ]
    if model_type & ENABLE_TOOL:
        model = model | tool_argument_injector({"ipython": {"thread_id": thread_id}})
        template = toolcall_template
    else:
        template = empty_template
    # 处理图片
    current_images = set(glob.iglob(f"media/{thread_id}/*.png"))
    # 新生成图片的message
    image_components = [
        component
        for image in current_images - state.get("images", current_images)
        if (component := create_image_component(image))
    ]
    image_messages = HumanMessage(image_components)
    # 生成附加图片的消息->加提示词模板->过滤->合并
    response = await model.ainvoke(
        merge_message_runs(
            apply_safety_filter(
                model_type,
                await template.ainvoke(
                    {
                        "messages": (
                            state["messages"]
                            if not image_components
                            else add_messages(state["messages"], image_messages)
                        )
                    }
                ),
            )
        )
    )
    # 添加生成图片
    return {"messages": [image_messages, response], "images": current_images}


# Agent构建
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


async def get_agent_app() -> CompiledStateGraph:
    """
    获取全局agent_app

    当agent_app未初始化，建立与数据库的连接并构建。应于程序运行后尽快调用
    """
    global agent_app, conn
    if agent_app is None:
        conn = await AsyncConnection.connect(
            DB_URI, autocommit=True, prepare_threshold=0, row_factory=dict_row
        )
        postgres_checkpointer = AsyncPostgresSaver(conn=conn)
        await postgres_checkpointer.setup()
        agent_app = graph_builder.compile(checkpointer=postgres_checkpointer)
    return agent_app


async def close_conn() -> None:
    """
    关闭与数据库的连接

    应于程序结束前调用
    """
    global conn
    await conn.close()
