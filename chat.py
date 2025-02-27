from modelclient import gpt_4o_mini, glm_4_flash, pixtral_large_latest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langchain_core.messages import HumanMessage, BaseMessage
import base64
from typing import Dict, Union


class DynamicMessagesState(MessagesState):
    multimodal: bool


workflow = StateGraph(state_schema=DynamicMessagesState)


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


# Define the function that calls the model
def call_model(
        state: DynamicMessagesState) -> Dict[str, Union[BaseMessage, int]]:
    message = state["messages"]
    if state['multimodal']:
        response = pixtral_large_latest.invoke(message)
    else:
        try:
            response = gpt_4o_mini.invoke(message)
        except:
            response = glm_4_flash.invoke(message)
    return {"messages": response}


# Define the (single) node in the graph
workflow.add_edge(START, "model")
workflow.add_node("model", call_model)

# Add memory
memory = MemorySaver()
chat_app = workflow.compile(checkpointer=memory)


def add_message(text, files, thread_id, multimodal):
    content = [
        {
            "type": "text",
            "text": text
        },
    ]
    for file in files:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{encode_image(file)}"
            }
        })
    input_message = [HumanMessage(content)]
    for chunk, _ in chat_app.stream(
        {
            "messages": input_message,
            "multimodal": multimodal
        },
            config={"configurable": {
                "thread_id": thread_id
            }},
            stream_mode="messages"):
        yield chunk.content


"""
{
                "url": f"data:image/png;base64,{encodedString}"
            }
input_messages = [HumanMessage(query)]
output = chat_app.stream({"messages": input_messages, "multimodal": False}, config, stream_mode = "messages")
for chunk, _ in output:
    print(chunk.content, end="")
def clear_memory(memory: BaseCheckpointSaver, thread_id: str) -> None:
    checkpoint = empty_checkpoint()
    memory.put(config={"configurable": {"thread_id": thread_id}}, checkpoint=checkpoint, metadata={})

# Calling the function

memory = SqliteSaver.from_conn_string("checkpoints.sqlite")
app = graph.compile(checkpointer=memory)

clear_memory(memory=memory, thread_id="123456")
"""
