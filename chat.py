import base64
import os
import re
from io import StringIO
from typing import Dict, Generator, List, Union

from langchain_core.messages import HumanMessage

from chat_backend import chat_app
from execute_code import insert_python

# Regular expression patterns
FORMULA_PATTERN = re.compile(r'\$\$\s*(.*?)\s*\$\$', re.DOTALL)
XML_TAG_PATTERN = re.compile(r"<(\w+)>(.*?)</\1>", re.DOTALL)

# Supported tools mapping
TOOLS = {'python': insert_python}


def encode_image(image_path: str) -> str:
    """Encode an image file to base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def format_formula(text: str) -> str:
    """Normalize LaTeX formula formatting."""
    return FORMULA_PATTERN.sub(
        r'$$\1$$',
        text.replace(r'\(', '$').replace(r'\)', '$')
            .replace(r'\[', '$$').replace(r']', '$$')
    )


def toolcall(message: str) -> str:
    """Process XML-like tags in message using registered tools."""
    def replace_tag(match: re.Match) -> str:
        tag = match.group(1)
        param = match.group(2).strip()
        if not param or tag not in TOOLS:
            return match.group(0)  # Return original if invalid
        return TOOLS[tag](param)
    
    return XML_TAG_PATTERN.sub(replace_tag, message)


def create_image_component(image_path: str) -> Dict[str, Union[str, Dict[str, str]]]:
    """Create an image component dictionary for chat messages."""
    return {
        "type": "image_url",
        "image_url": {
            "url": f"data:image/png;base64,{encode_image(image_path)}"
        }
    }


def add_message(
    text: str,
    files: List[str],
    thread_id: str,
    multimodal: bool,
    now_time: str
) -> Generator[str, None, None]:
    """Add a message to the chat and stream processed responses."""
    chat_config = {"configurable": {"thread_id": thread_id}}
    
    # Build message content
    content = [{"type": "text", "text": text}]
    content.extend(create_image_component(f) for f in files)
    
    response_buffer = StringIO()
    
    # Stream chat response chunks
    for chunk, _ in chat_app.stream(
        {
            "messages": [HumanMessage(content=content)],
            "multimodal": multimodal,
            "now_time": now_time
        },
        config=chat_config,
        stream_mode="messages"
    ):
        response_buffer.write(chunk.content)
        yield response_buffer.getvalue()
    
    # Process final response
    final_response = toolcall(response_buffer.getvalue())
    final_response = format_formula(final_response)
    
    # Check for generated image
    generated_image = f"{now_time}.png"
    if os.path.exists(generated_image):
        chat_app.update_state(
            chat_config,
            {"messages": HumanMessage([create_image_component(generated_image)])}
        )
    
    yield final_response
