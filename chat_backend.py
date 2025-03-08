from typing import Dict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from system_prompt import REGEX_TOOLCALL, WEB_SEARCH, KNOWLEDGEBASE
from modelclient import (
    gpt_4o_mini,
    glm_4_flash,
    pixtral_large_latest,
    deepseek_v3,
    deepseek_r1_671b,
    deepseek_r1_70b,
)


# Define the prompt template
regex_toolcall_template = ChatPromptTemplate.from_messages(
    [("system", REGEX_TOOLCALL), MessagesPlaceholder(variable_name="messages")]
)
web_search_template = ChatPromptTemplate.from_messages(
    [("system", WEB_SEARCH), MessagesPlaceholder(variable_name="messages")]
)
knowledgebase_template = ChatPromptTemplate.from_messages(
    [("system", KNOWLEDGEBASE), MessagesPlaceholder(variable_name="messages")]
)


# State class for managing dynamic messages
class ChatMessageState(MessagesState):
    mode: str
    now_time: str


select_template_from_mode = {
    "常规": regex_toolcall_template,
    "多模态": None,
    "知识库": knowledgebase_template,
    "网页搜索": web_search_template,
}


def chat_call_model(state: ChatMessageState) -> Dict[str, BaseMessage]:
    """
    Invoke the appropriate model based on the state and return the response.

    Args:
        state: The current state containing messages and other attributes.

    Returns:
        A dictionary containing the response message.
    """
    message = state["messages"]
    template = select_template_from_mode[state["mode"]]

    if template is not None:
        prompted_message = template.invoke(state)
        response = deepseek_v3.invoke(prompted_message)
    else:
        response = pixtral_large_latest.invoke(message)

    return {"messages": response}


# Create the chat_workflow graph
chat_workflow = StateGraph(state_schema=ChatMessageState)
chat_workflow.add_edge(START, "model")
chat_workflow.add_node("model", chat_call_model)

# Initialize chat_memory saver and compile the chat application
chat_memory = MemorySaver()
chat_app = chat_workflow.compile(checkpointer=chat_memory)


class SolveMessageState(MessagesState):
    distill: int


def solve_call_model(state: SolveMessageState) -> Dict[str, BaseMessage]:
    distill = state["distill"]
    if distill == 0:
        response = deepseek_r1_70b.invoke(state["messages"])
    elif distill == 1:
        response = deepseek_r1_671b.invoke(state["messages"])
    return {"messages": response}


solve_workflow = StateGraph(state_schema=SolveMessageState)
solve_workflow.add_edge(START, "model")
solve_workflow.add_node("model", solve_call_model)

solve_memory = MemorySaver()
solve_app = solve_workflow.compile(checkpointer=solve_memory)
