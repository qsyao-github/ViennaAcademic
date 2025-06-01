import glob
from typing import AsyncGenerator, List

import orjson
from chat_utils.chat import astream_response
from llm_utils.modelclient import model_type

# 文件类型
ALLOWED_IMAGE_TYPE = frozenset(["image/jpeg", "image/png"])
ALLOWED_PAPER_TYPE = frozenset(
    [
        "text/plain",  # plain text
        "text/html",  # html
        "text/xml",  # xml
        "text/csv",  # csv
        "application/epub+zip",  # epub
        "application/json",  # json
        "application/rtf",  # rtf
        "application/vnd.oasis.opendocument.text",  # odt
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
        "application/pdf",  # pdf - marker
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # pptx - marker
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx - marker
    ]
)


async def respond_stream(
    query: str,
    image_urls: List[str],
    file_urls: List[str],
    thread_id: str,
    model: str,
    enable_tool: bool,
    enable_thinking: bool,
    multimodal: bool,
) -> AsyncGenerator[bytes, None]:
    """
    生成模型回复字节流

    Parameters
    ----------
    query: str
        用户文本输入
    image_urls: List[str]
        用户上传的图片url列表
    file_urls: List[str]
        用户引用的文件url列表
    thread_id:
        线程唯一标识符
    model: str
        模型名称
    enable_tool: bool
        启用工具调用
    enable_thinking: bool
        启用思考
    multimodal: bool
        支持多模态

    Yields
    ----------
    bytes
        模型回复字节流

    Notes
    ----------
    1. 当前可用的模型列表中未能找到模型名称和模型类型匹配的模型，返回{"ERROR": "No such model"}
    2. 正常返回值有
        - {"content": "正文片段"}
        - {"tool_calls": "工具调用json字符串片段"}
        - {"reasoning_content": "推理片段"}
        - {"image_urls": ["/path/to/model/generated/image_1", "/path/to/model/generated/image_2"]}
    """
    # 流式输出
    bot_response = astream_response(
        query,
        image_urls,
        file_urls,
        thread_id,
        model,
        model_type(enable_tool, enable_thinking, multimodal),
    )
    try:
        async for response_chunk in bot_response:
            yield orjson.dumps(response_chunk)

        # 附加图片
        yield orjson.dumps(
            f"""event: image_output\ndata: {{content: {[
                    f"/{path}" for path in glob.glob(f"media/{thread_id}/*.png")
                ]}}}"""
        )
    except Exception as e:
        yield orjson.dumps(
            f"""event: systen\ndata: {{type: "error", notice: "{e}"}}\n\n"""
        )
