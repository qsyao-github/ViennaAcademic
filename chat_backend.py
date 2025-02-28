from modelclient import gpt_4o_mini, glm_4_flash, pixtral_large_latest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langchain_core.messages import BaseMessage

from typing import Dict
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

prompt_template = ChatPromptTemplate.from_messages([
    (
        "system",
        """你是强大的LLM Agent，你可以通过魔术命令上网、制作动画、执行Python代码。命令形如<function_name>params</function_name>。若你需要上网搜索，请在回答中加入"<websearch>关键字</websearch>"；若你需要使用manim制作动画，请在回答中加入"<manim>代码</manim>"。若你需要运行Python代码，请在回答中加入"<python>代码</python>"。你可以使用numpy, scipy, sympy, matplotlib。请将绘制的图表保存至{now_time}.png""",
    ),
    MessagesPlaceholder(variable_name="messages"),
])


class DynamicMessagesState(MessagesState):
    multimodal: bool
    now_time: str


workflow = StateGraph(state_schema=DynamicMessagesState)


# Define the function that calls the model
def call_model(state: DynamicMessagesState) -> Dict[str, BaseMessage]:
    message = state["messages"]
    if state['multimodal']:
        print('multimodal')
        response = pixtral_large_latest.invoke(message)
    else:
        prompted_message = prompt_template.invoke(state)
        try:
            response = gpt_4o_mini.invoke(prompted_message)
        except:
            response = glm_4_flash.invoke(prompted_message)
    return {"messages": response}


workflow.add_edge(START, "model")
workflow.add_node("model", call_model)
memory = MemorySaver()
chat_app = workflow.compile(checkpointer=memory)
