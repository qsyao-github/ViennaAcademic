"""
fastapi端点的辅助函数/类/变量
"""

import shutil
from pathlib import Path
from typing import AsyncGenerator, List

from chat_utils.agent_backend import ModelInfo, models
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
) -> AsyncGenerator[str, None]:
    """
    生成模型回复流

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
    str
        模型回复流

    Notes
    ----------
    可能返回system(错误), chat(一般文本片段), tool_call(工具调用json片段), reasoning(推理内容片段), image_output(生成图片列表)
    """
    # 获取模型，处理模型错误的情况
    model_type_code = model_type(enable_tool, enable_thinking, multimodal)
    if not models.get(ModelInfo(model, model_type_code)):
        yield """event: system\ndata: {type: "error", notice: "No such model"}\n\n"""
        return
    # 流式输出
    bot_response = astream_response(
        query,
        image_urls,
        file_urls,
        thread_id,
        model,
        model_type_code,
    )
    try:
        async for response_chunk in bot_response:
            yield response_chunk
    except Exception as e:
        yield f"""event: system\ndata: {{type: "error", notice: "{e}"}}\n\n"""


def delete_file(path: Path) -> None:
    """
    删除单个文件或目录

    Parameters
    ----------
    path: Path
        文件或目录路径
    """
    if path.is_file():
        path.unlink()
    else:
        shutil.rmtree(path)
