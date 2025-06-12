"""
后端入口文件，fastapi app主体

运行：
uvicorn fastapi_endpoint:app --host 0.0.0.0 --port 8000 --loop uvloop
"""

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from typing import Annotated, List, Literal

import aiofiles
import magic
import uvloop
from auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    Token,
    User,
    authenticate_user,
    create_access_token,
    get_current_user,
)
from chat_utils.agent_backend import (
    available_models,
    close_conn,
    get_agent_app,
)
from endpoint_utils import (
    ALLOWED_IMAGE_TYPE,
    ALLOWED_PAPER_TYPE,
    delete_file,
    paper_stream,
    respond_stream,
)
from fastapi import Depends, FastAPI, HTTPException, UploadFile, status
from fastapi.responses import ORJSONResponse, PlainTextResponse, StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles

# from file_utils.file_conversion import everything_to_markdown
from llm_utils.modelclient import close_models, init_models
from pydantic import BaseModel
from va_rust_utils import markdown_to_everything, initialize_static

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    await get_agent_app()
    initialize_static()
    yield
    await close_models()
    await close_conn()


app = FastAPI(lifespan=lifespan, default_response_class=ORJSONResponse)

app.mount("/media", StaticFiles(directory="media"), name="media")
app.mount("/documents", StaticFiles(directory="documents"), name="documents")

# 用户系统


@app.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """
    获取jwt token
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(
        access_token=create_access_token(
            data={"sub": user.username},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        ),
        token_type="bearer",
    )


# 文件系统


@app.post("/upload/image/{thread_id}", response_class=PlainTextResponse)
async def upload_image(
    file: UploadFile, thread_id: str, _user: Annotated[User, Depends(get_current_user)]
):
    """
    在{thread_id}对话中上传图片

    示例输出：
    ```json
    "/media/somethread/imagename"
    ```
    """
    # 类型验证
    chunk = await file.read(2048)

    if (detected_mime := magic.from_buffer(chunk, mime=True)) not in ALLOWED_IMAGE_TYPE:
        raise HTTPException(
            400, detail=f"Only png, jpg, jpeg are allowed. Got {detected_mime}"
        )
    await file.seek(0)

    # 异步流式上传
    folder_path = os.path.join("media", thread_id)
    # 防止路径遍历
    final_path = os.path.join(folder_path, os.path.basename(file.filename))
    os.makedirs(folder_path, exist_ok=True)
    async with aiofiles.open(final_path, "wb") as f:
        while chunk := await file.read(8192):
            await f.write(chunk)
    return f"/{final_path}"


'''@app.post("/upload/document/paper", response_class=PlainTextResponse)
async def upload_paper(
    file: UploadFile, user: Annotated[User, Depends(get_current_user)]
):
    """
    用户上传论文，支持纯文本, tex, html, xml, epub, json, rtf, docx, xlsx, pptx, odt, pdf

    示例输出：
    ```json
    "/documents/example_user/paper/filename.pdf"
    ```
    """
    # 防止路径遍历
    final_path = os.path.join(
        "documents", user.username, "paper", os.path.basename(file.filename)
    )

    # 类型验证
    chunk = await file.read(2048)

    detected_mime = magic.from_buffer(chunk, mime=True)

    # 重复上传保护
    if not os.path.exists(final_path):
        if detected_mime not in ALLOWED_PAPER_TYPE:
            raise HTTPException(
                400,
                detail=f"Only plain text, tex, html, xml, epub, json, rtf, docx, xlsx, pptx, odt, pdf are allowed. Got {detected_mime}",
            )
        await file.seek(0)

        # 异步流式上传
        async with aiofiles.open(final_path, "wb") as f:
            while chunk := await file.read(8192):
                await f.write(chunk)

    # 非纯文本解析
    if detected_mime != "text/plain":
        await everything_to_markdown(
            final_path, os.path.join("documents", user.username, "knowledgeBase")
        )
    return f"/{final_path}"'''


@app.post("/upload/document/code", response_class=PlainTextResponse)
async def upload_code(
    file: UploadFile, user: Annotated[User, Depends(get_current_user)]
):
    """
    用户上传代码，支持文本文件

    示例输出：
    ```json
    "/documents/example_user/code/program.py"
    ```
    """
    # 重复上传保护，防止路径遍历
    final_path = os.path.join(
        "documents", user.username, "code", os.path.basename(file.filename)
    )
    if os.path.exists(final_path):
        return f"/{final_path}"

    # 类型验证
    chunk = await file.read(2048)

    if not (detected_mime := magic.from_buffer(chunk, mime=True)).startswith("text/"):
        raise HTTPException(
            400,
            detail=f"Only text files are allowed. Got {detected_mime}",
        )
    await file.seek(0)

    # 异步流式上传
    async with aiofiles.open(final_path, "wb") as f:
        while chunk := await file.read(8192):
            await f.write(chunk)
    return f"/{final_path}"


@app.get("/list_files/{directory}")
async def list_directory(
    user: Annotated[User, Depends(get_current_user)],
    directory: Literal["paper", "knowledgeBase", "code", "tempest", "convert"],
):
    """
    列出用户的{directory}内的所有文件

    示例输出：
    ```json
    [
        "/documents/example_user/code/backend.rs",
        "/documents/example_user/code/frontend.py"
    ]
    ```
    """
    return [
        f"/documents/{user.username}/{directory}/{entry.name}"
        for entry in os.scandir(os.path.join("documents", user.username, directory))
    ]


class DeleteRequests(BaseModel):
    file_urls: List[str]


@app.post("/delete")
async def delete_files(
    files: DeleteRequests, user: Annotated[User, Depends(get_current_user)]
):
    """
    删除文件或目录

    输入示例：
    ```json
    {
        "file_urls": [
            "/documents/user/paper/1706.03762.pdf",
            "/media/thread_1",
            "/media/thread_2/image.png"
        ]
    }
    ```
    非法路径将被忽略
    目前此端口一定返回null
    """
    document_path = Path(f"documents/{user.username}").resolve()
    media_path = Path("media").resolve()

    # 合法性检验，在documents对应用户文件夹下或media下的文件才允许删除
    for url in files.file_urls:
        if (path := Path(url.strip("/")).resolve()).exists() and (
            path.is_relative_to(document_path) or path.is_relative_to(media_path)
        ):
            delete_file(path)


# 聊天


class ChatQuery(BaseModel):
    query: str
    image_urls: List[str]
    file_urls: List[str]
    model: str
    enable_tool: bool = False
    enable_thinking: bool = False
    multimodal: bool = False


@app.post("/chat/{thread_id}")
async def respond(
    _user: Annotated[User, Depends(get_current_user)],
    thread_id,
    chat_query: ChatQuery,
):
    """
    聊天请求

    输入示例：
    ```json
    {
        "query": "请帮我看一下这段代码生成的图片",
        "image_urls": [
            "/media/thread_id/code_generated_image.png"
        ],
        "file_urls": [
            "/documents/example_user/code/plot.py"
        ],
        "model": "mistral-small",
        "enable_tool": false,
        "enable_thinking": false,
        "multimodal": true
    }
    ```
    输出示例：
    ```
    event: chat
    data: {content: "chat_buffer"}

    event: tool_call
    data: {content: "tool_call_buffer"}

    event: tool_result
    data: {content: "tool_result"}

    event: reasoning
    data: {content: "reasoning_buffer"}

    event: image_output
    data: {content: ["/media/thread_id/code_generated_image1.png", "/media/thread_id/code_generated_image2.png"]}
    ```
    """
    query = chat_query.query.strip()
    image_urls = chat_query.image_urls
    multimodal = chat_query.multimodal
    file_urls = chat_query.file_urls
    if not (query or (image_urls and multimodal) or file_urls):
        raise HTTPException(400, detail="Empty query")
    return StreamingResponse(
        respond_stream(
            query,
            image_urls,
            file_urls,
            thread_id,
            chat_query.model,
            chat_query.enable_tool,
            chat_query.enable_thinking,
            multimodal,
        ),
        media_type="text/event-stream",
    )


@app.get("/models")
async def get_model_list():
    """
    获取各种类型的可用模型

    每类均按个人观点对能力由强到弱排序，每类都有至少一个免费模型

    示例输出：
    ```json
    [
        {
            "enable_tool": false,
            "enable_reasoning": false,
            "multimodal": false,
            "models": [
                "deepseek-v3",
                "qwen3-235b-a22b",
                "qwen3-8b"
            ]
        },
        {
            "enable_tool": false,
            "enable_reasoning": false,
            "multimodal": true,
            "models": [
                "qwen2.5-vl-72b",
                "mistral-small"
            ]
        },
        {
            "enable_tool": false,
            "enable_reasoning": true,
            "multimodal": false,
            "models": [
                "deepseek-r1-671b",
                "qwen3-235b-a22b",
                "deepseek-r1-qwen3-8b"
            ]
        },
        {
            "enable_tool": true,
            "enable_reasoning": false,
            "multimodal": false,
            "models": [
                "deepseek-v3",
                "qwen3-235b-a22b",
                "qwen3-8b"
            ]
        },
        {
            "enable_tool": true,
            "enable_reasoning": true,
            "multimodal": false,
            "models": [
                "qwen3-235b-a22b",
                "qwen3-8b"
            ]
        }
    ]
    ```
    """
    return available_models


@app.post("/delete_thread/{thread_id}")
async def delete_thread(thread_id: str):
    """
    删除后端某个对话线程的历史记录

    目前此端口一定返回null

    这是一个暂时的实现，后续可能要考虑根据上次对话时间删除历史记录
    """
    await (await get_agent_app()).checkpointer.adelete_thread(thread_id)


# 论文


class PaperQuery(BaseModel):
    file_url: str
    function: Literal["read", "translate_to_Chinese", "translate_to_English", "polish"]


@app.post("/paper")
async def paper_response_stream(
    paper_query: PaperQuery,
    user: Annotated[User, Depends(get_current_user)],
):
    """
    论文模块请求

    目前支持四种模式：
    - read: 论文解读
    - translate_to_Chinese: 论文翻译为中文
    - translate_to_English: 论文翻译为英文
    - polish: 论文润色

    输入示例：
    ```json
    {
        "file_url": "/documents/example_user/paper/1706.03762.pdf",
        "function": "read"
    }
    ```
    输出示例：
    ```
    event: read_paper
    data: {content: "paper_interpretation_buffer"}

    event: process_paper
    data: {content: "a_translated_or_polished_paragraph_or_newline"}
    ```

    当文件为空/模型错误返回
    ```
    event: system
    data: {type: "error", notice: "error_message"}
    ```

    当文件不存在或无权限，返回HTTP状态码400

    论文解读流式返回模型生成的token。其余模式以段落为单位返回处理后文本。为校准分段，可能存在整个段落仅有单个换行符的情况。前端仅需按顺序将所有文本拼接即可，不需处理分段换行的逻辑。
    """
    # 合法性检验，在documents对应用户文件夹下的文件才允许访问
    if (file_path := Path(paper_query.file_url.strip("/ ")).resolve()).exists() and (
        file_path.is_relative_to(Path(f"documents/{user.username}").resolve())
    ):
        return StreamingResponse(
            paper_stream(paper_query.file_url, paper_query.function, user.username),
            media_type="text/event-stream",
        )
    raise HTTPException(400, detail="File not found")


# 文件转换


class ConvertQuery(BaseModel):
    file_url: str
    format: Literal[
        "docx", "pdf", "tex", "typ", "pptx", "html", "xml", "epub", "json", "rtf"
    ]


@app.post("/convert")
async def convert_file(
    convert_query: ConvertQuery, user: Annotated[User, Depends(get_current_user)]
):
    """
    markdown导出请求，支持docx, pdf, tex, typ, pptx, html, xml, epub, json, rtf

    推荐转换为docx, pdf, tex(latex源文件格式), typ(typst源文件格式)。pptx对于分段复杂的文本效果较差，json实用性较低，其余格式使用场景不多。

    pdf由pandoc转换为typ，经少量预处理后再由typst转换为pdf。其余均由pandoc直接转换。

    输入示例：
    ```json
    {
        "file_url": "/documents/example_user/knowledgeBase/1706.03762.md",
        "format": "docx"
    }
    ```

    输出示例：
    ```
    /documents/example_user/convert/1706.03762.docx
    ```

    当转换失败或文件不存在或无权限，HTTP状态码为400
    """
    file_url = convert_query.file_url.strip("/")
    format = convert_query.format
    if (file_path := Path(file_url).resolve()).exists() and (
        file_path.is_relative_to(Path(f"documents/{user.username}").resolve())
    ):
        convert_dir_path = os.path.join("documents", user.username, "convert")
        markdown_to_everything(file_url, convert_dir_path, format)
        convert_file_path = os.path.join(
            convert_dir_path,
            f"{file_path.stem}.{format}",
        )
        if os.path.exists(convert_file_path):
            return f"/{convert_file_path}"
        raise HTTPException(400, detail="Conversion failed")
    raise HTTPException(400, detail="File not found")
