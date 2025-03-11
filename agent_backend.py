from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, MessagesState
from langgraph.graph.message import add_messages, BaseMessage
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from system_prompt import REGEX_TOOLCALL, WEB_SEARCH, KNOWLEDGEBASE
from execute_code import python_tool
from search import attach_web_result
from langchain_core.tools import tool
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
    filter_messages,
    convert_to_messages,
    merge_message_runs,
)

from modelclient import (
    gpt_4o_mini,
    glm_4_flash,
    pixtral_large_latest,
    deepseek_v3,
    deepseek_r1_671b,
    deepseek_r1_70b,
    qwq_32b,
)

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


class ChatMessageState(MessagesState):
    mode: str
    now_time: str


@tool
def websearch(query: str) -> str:
    """使用搜索引擎"""
    return attach_web_result(query)


@tool
def ipython(code: str) -> str:
    """使用IPython。用numpy、scipy、sympy做数值、符号计算，用matplotlib绘图"""
    return python_tool(code)


graph_builder = StateGraph(ChatMessageState)
tools = [ipython, websearch]
deepseek_v3_with_tools = deepseek_v3.bind_tools(tools)
select_model_from_mode = {
    "常规": deepseek_v3_with_tools,
    "多模态": pixtral_large_latest,
    "知识库": deepseek_v3,
    "网页搜索": deepseek_v3,
}

# from langchain_core.messages import filter_messages
def filter_tools(messages):
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


def filter_multimodal(messages):
    messages = convert_to_messages(messages)
    filtered: list[BaseMessage] = []
    for message in messages:
        if isinstance(message, HumanMessage):
            filtered.append(
                HumanMessage(
                    content=[
                        chunk for chunk in message.content if chunk["type"] == "text"
                    ] or [{'type': 'text', 'text': '系统提示：用户没有输入任何内容，请礼貌的要求用户输入文本或使用多模态模式'}]
                )
            )
        elif isinstance(message, AIMessage) or isinstance(message, SystemMessage):
            filtered.append(message)
    return filtered


def chatbot(state: ChatMessageState):
    mode = state["mode"]
    template = select_template_from_mode[mode]
    model = select_model_from_mode[mode]
    prompted_message = template.invoke(state)
    if mode != "多模态":
        prompted_message = filter_multimodal(prompted_message)
    if mode != "常规":
        prompted_message = filter_tools(prompted_message)
    merged = merge_message_runs(prompted_message)
    response = model.invoke(merged)
    return {"messages": response}


"""AIMessage(content='', additional_kwargs={'tool_calls': [{'index': 0, 'id': 'call_a62zpuxfjk0phwgz2m3382mx', 'function': {'arguments': '{"code":"import numpy as np\\nimport matplotlib.pyplot as plt\\n\\nx = np.linspace(0, 2 * np.pi, 1000)\\ny = np.sin(x)\\n\\nplt.plot(x, y)\\nplt.title(\'Plot of sin(x)\')\\nplt.xlabel(\'x\')\\nplt.ylabel(\'sin(x)\')\\nplt.grid(True)\\nplt.savefig(\'250311130554.png\')\\nplt.show()"}', 'name': 'ipython'}, 'type': 'function'}]}, response_metadata={'finish_reason': 'tool_calls', 'model_name': 'deepseek-v3-241226'}, id='run-b6b04698-3d18-43fc-be98-38d0b284bbd5', tool_calls=[{'name': 'ipython', 'args': {'code': "import numpy as np\nimport matplotlib.pyplot as plt\n\nx = np.linspace(0, 2 * np.pi, 1000)\ny = np.sin(x)\n\nplt.plot(x, y)\nplt.title('Plot of sin(x)')\nplt.xlabel('x')\nplt.ylabel('sin(x)')\nplt.grid(True)\nplt.savefig('250311130554.png')\nplt.show()"}, 'id': 'call_a62zpuxfjk0phwgz2m3382mx', 'type': 'tool_call'}])"""

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
