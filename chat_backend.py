# Third-party imports
from modelclient import gpt_4o_mini, glm_4_flash, pixtral_large_latest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from typing import Dict

# Define the prompt template
prompt_template = ChatPromptTemplate.from_messages([
    (
        "system",
        """你是强大的LLM Agent，你可以通过魔术命令上网、制作动画、执行Python代码。命令形如<function_name>params</function_name>。若你需要上网搜索，请在回答中加入"<websearch>关键字</websearch>"；若你需要使用manim制作动画，请在回答中加入"<manim>代码</manim>"。若你需要运行Python代码，请在回答中加入"<python>代码</python>"。你可以使用numpy, scipy, sympy, matplotlib。请将绘制的图表保存至{now_time}.png""",
    ),
    MessagesPlaceholder(variable_name="messages"),
])


# State class for managing dynamic messages
class DynamicMessagesState(MessagesState):
    """State class for managing dynamic messages with additional attributes."""

    multimodal: bool
    now_time: str


def call_model(state: DynamicMessagesState) -> Dict[str, BaseMessage]:
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
        prompted_message = prompt_template.invoke(state)
        try:
            response = gpt_4o_mini.invoke(prompted_message)
        except Exception as e:
            # Log the exception
            import logging
            logging.error(f"An error occurred while invoking GPT-4o-mini: {e}")
            # Fallback to another model
            response = glm_4_flash.invoke(prompted_message)

    return {"messages": response}


# Create the workflow graph
workflow = StateGraph(state_schema=DynamicMessagesState)
workflow.add_edge(START, "model")
workflow.add_node("model", call_model)

# Initialize memory saver and compile the chat application
memory = MemorySaver()
chat_app = workflow.compile(checkpointer=memory)
