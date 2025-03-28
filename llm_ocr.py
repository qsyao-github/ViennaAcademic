"""
解题功能识别题目的模块
"""

from chat_utils.media_handler import create_image_component
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from modelclient import glm_4v_flash

ocr_prompt_template = ChatPromptTemplate(
    [
        ("system", "请准确返回题目的文字与公式，不要返回其它内容"),
        MessagesPlaceholder(variable_name="messages"),
    ]
)


def file_ocr(file: str) -> str:
    """识别图片中的文字和公式

    Parameters
    ----------
    file : str
        图片文件路径

    Returns
    ----------
    str
        识别结果
    """
    ocr_prompt = ocr_prompt_template.invoke(
        {"messages": [HumanMessage(content=[create_image_component(file)])]}
    )
    response = glm_4v_flash.invoke(ocr_prompt)
    return response.content
