from modelclient import glm_4v_flash
from chat import MediaHandler, ContentProcessor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage

ocr_prompt_template = ChatPromptTemplate(
    [
        ("system", "请准确返回题目的文字与公式，不要返回其它内容"),
        MessagesPlaceholder(variable_name="messages"),
    ]
)


def file_ocr(file: str) -> str:
    ocr_prompt = ocr_prompt_template.invoke(
        {"messages": [HumanMessage(content=[MediaHandler.create_image_component(file)])]}
    )
    response = glm_4v_flash.invoke(ocr_prompt)
    return ContentProcessor.format_formula(response.content)
