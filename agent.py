from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from execute_code import python_tool
from search import attach_web_result
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from system_prompt import REGEX_TOOLCALL
from modelclient import deepseek_v3, qwq_32b

regex_toolcall_template = ChatPromptTemplate.from_messages(
    [("system", REGEX_TOOLCALL), MessagesPlaceholder(variable_name="messages")]
)


class ChatAgentState(AgentState):
    now_time: str


@tool
def websearch(query: str) -> str:
    """使用搜索引擎"""
    return attach_web_result(query)


@tool
def ipython(code: str) -> str:
    """使用IPython。用numpy、scipy、sympy做数值、符号计算，用matplotlib绘图"""
    return python_tool(code)


# Create the agent
chat_memory = MemorySaver()
tools = [ipython, websearch]
chat_agent_executor = create_react_agent(
    deepseek_v3,
    tools,
    checkpointer=chat_memory,
    prompt=regex_toolcall_template.invoke,
    state_schema=ChatAgentState,
)

solve_memory = MemorySaver()
solve_agent_executor = create_react_agent(qwq_32b, [ipython], checkpointer=solve_memory)
