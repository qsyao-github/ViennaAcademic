from chat_backend import chat_app
from io import StringIO
from langchain_core.messages import HumanMessage
import base64
import re
import os
from execute_code import insert_python

FORMAT_FORMULA_PATTERN = re.compile(r'\$\$[\s]*(.*?)\s*[\s]*\$\$',
                                    flags=re.DOTALL)
XML_PATTERN = re.compile(r"<(\w+)>(.*?)</\1>", re.DOTALL)
tools = {'python': insert_python}


def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def format_formula(text):
    return FORMAT_FORMULA_PATTERN.sub(
        r'$$\1$$',
        text.replace('\\(',
                     '$').replace('\\)',
                                  '$').replace('\\[',
                                               '$$').replace('\\]', '$$'))


def toolcall(message: str):
    matches = XML_PATTERN.findall(message)
    for tag, param in matches:
        if param.strip():
            tool_to_call = tools.get(tag, None)
            if tool_to_call:
                replacement = tool_to_call(param.strip())
                print(replacement)
                message = message.replace(f"<{tag}>{param}</{tag}>",
                                          replacement)
    return message


def add_message(text, files, thread_id, multimodal, now_time):
    current_config = {"configurable": {"thread_id": thread_id}}
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
    response = StringIO()
    for chunk, _ in chat_app.stream(
        {
            "messages": input_message,
            "multimodal": multimodal,
            "now_time": now_time
        },
            config=current_config,
            stream_mode="messages"):
        response.write(chunk.content)
        yield response.getvalue()
    final_response = toolcall(response.getvalue())
    final_response = format_formula(final_response)
    for png_file in os.listdir():
        if png_file.endswith(".png"):
            chat_app.update_state(
                current_config, {
                    'messages':
                    HumanMessage([{
                        "type": "image_url",
                        "image_url": {
                            "url":
                            f"data:image/png;base64,{encode_image(png_file)}"
                        }
                    }])
                })
            print(chat_app.get_state(current_config))
    yield final_response
