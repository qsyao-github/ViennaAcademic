from typing import Dict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from modelclient import (
    gpt_4o_mini,
    glm_4_flash,
    pixtral_large_latest,
    deepseek_v3,
    deepseek_r1_671b,
    deepseek_r1_70b,
)


# Define the prompt template
chat_prompt_template = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """你是强大的LLM Agent，你可以通过魔术命令上网、制作动画、执行Python代码。命令形如<function_name>params</function_name>。若你需要上网搜索，请在回答中加入"<websearch>关键字</websearch>"；若你需要使用manim制作动画，请在回答中加入"<manim>代码</manim>"。若你需要运行Python代码，请在回答中加入"<python>代码</python>"。你可以使用numpy, scipy, sympy, matplotlib。请将绘制的图表保存至{now_time}.png""",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
)


# State class for managing dynamic messages
class ChatMessageState(MessagesState):
    multimodal: bool
    now_time: str


def chat_call_model(state: ChatMessageState) -> Dict[str, BaseMessage]:
    """
    Invoke the appropriate model based on the state and return the response.

    Args:
        state: The current state containing messages and other attributes.

    Returns:
        A dictionary containing the response message.
    """
    message = state["messages"]

    if state["multimodal"]:
        response = pixtral_large_latest.invoke(message)
    else:
        prompted_message = chat_prompt_template.invoke(state)
        response = deepseek_v3.invoke(prompted_message)

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
    distill = state['distill']
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
