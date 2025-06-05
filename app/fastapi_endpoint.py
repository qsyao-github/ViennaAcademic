"""
运行：
uvicorn fastapi_endpoint:app --host 0.0.0.0 --port 8000 --loop uvloop
"""

import asyncio
import os
import shutil
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
from endpoint_utils import ALLOWED_IMAGE_TYPE, ALLOWED_PAPER_TYPE, respond_stream
from fastapi import Depends, FastAPI, HTTPException, UploadFile, status
from fastapi.responses import ORJSONResponse, PlainTextResponse, StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from llm_utils.modelclient import close_models, init_models
from pydantic import BaseModel

# from file_utils.file_conversion import everything_to_markdown

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


@asynccontextmanager
async def lifespan(app: FastAPI):

    await init_models()
    await get_agent_app()
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
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


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

    detected_mime = magic.from_buffer(chunk, mime=True)
    if detected_mime not in ALLOWED_IMAGE_TYPE:
        raise HTTPException(
            400, detail=f"Only png, jpg, jpeg are allowed. Got {detected_mime}"
        )
    await file.seek(0)

    # 异步流式上传
    folder_path = os.path.join("media", thread_id)
    final_path = os.path.join(
        folder_path, os.path.basename(file.filename)
    )  # 防止路径遍历
    os.makedirs(folder_path, exist_ok=True)
    async with aiofiles.open(final_path, "wb") as f:
        while chunk := await file.read(8192):
            await f.write(chunk)
    return f"/{final_path}"


''' @app.post("/upload/document/paper", response_class=PlainTextResponse)
async def upload_paper(
    file: UploadFile, user: Annotated[User, Depends(get_current_user)]
):
    """
    用户上传论文，支持纯文本, html, xml, epub, json, rtf, docx, xlsx, pptx, odt, pdf

    示例输出：
    ```json
    "/documents/example_user/paper/filename.pdf"
    ```
    """
    # 重复上传保护
    final_path = os.path.join("documents", user.username, "paper", os.path.basename(file.filename))    # 防止路径遍历

    # 类型验证
    chunk = await file.read(2048)

    detected_mime = magic.from_buffer(chunk, mime=True)
    if not os.path.exists(final_path):
        if detected_mime not in ALLOWED_PAPER_TYPE:
            raise HTTPException(
                400,
                detail=f"Only plain text, html, xml, epub, json, rtf, docx, xlsx, pptx, odt, pdf are allowed. Got {detected_mime}",
            )
        await file.seek(0)

        # 异步流式上传
        async with aiofiles.open(final_path, "wb") as f:
            while chunk := await file.read(8192):
                await f.write(chunk)
    if detected_mime != "text/plain":
        knowledgeBase_path = os.path.join("documents", user.username, "knowledgeBase")
        await everything_to_markdown(final_path, knowledgeBase_path)
    return f"/{final_path}" '''


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
    # 重复上传保护
    final_path = os.path.join(
        "documents",
        user.username,
        "code",
        os.path.basename(file.filename),  # 防止路径遍历
    )
    if os.path.exists(final_path):
        return f"/{final_path}"

    # 类型验证
    chunk = await file.read(2048)

    detected_mime = magic.from_buffer(chunk, mime=True)
    if not detected_mime.startswith("text/"):
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
    """
    dir_path = os.path.join("documents", user.username, directory)
    return [
        f"/documents/{user.username}/{directory}/{entry.name}"
        for entry in os.scandir(dir_path)
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
    for item in (
        path
        for url in files.file_urls
        if (path := Path(url.strip("/")).resolve()).exists()  # 合法性检验
        and (
            path.is_relative_to(document_path) or path.is_relative_to(media_path)
        )  # 防止路径遍历，删除非法文件
    ):
        if item.is_file():
            item.unlink()
        else:
            shutil.rmtree(item)


# 模型回复


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
    """
    if not (
        chat_query.query
        or (chat_query.image_urls and chat_query.multimodal)
        or chat_query.file_urls
    ):
        raise HTTPException(400, detail="Empty query")
    return StreamingResponse(
        respond_stream(
            chat_query.query,
            chat_query.image_urls,
            chat_query.file_urls,
            thread_id,
            chat_query.model,
            chat_query.enable_tool,
            chat_query.enable_thinking,
            chat_query.multimodal,
        ),
        media_type="text/event-stream",
    )


@app.get("/models")
async def get_model_list():
    """
    获取各种类型的可用模型

    示例输出：
    ```json
    [
        {
            "enable_tool": false,
            "enable_reasoning": false,
            "multimodal": false,
            "models": [
                "deepseek-v3",
                "qwen3"
            ]
        },
        {
            "enable_tool": false,
            "enable_reasoning": false,
            "multimodal": true,
            "models": [
                "mistral-small"
            ]
        },
        {
            "enable_tool": false,
            "enable_reasoning": true,
            "multimodal": false,
            "models": [
                "deepseek-r1",
                "glm-z1-flash",
                "qwen3"
            ]
        },
        {
            "enable_tool": true,
            "enable_reasoning": false,
            "multimodal": false,
            "models": [
                "deepseek-v3",
                "qwen3"
            ]
        },
        {
            "enable_tool": true,
            "enable_reasoning": true,
            "multimodal": false,
            "models": [
                "qwen3"
            ]
        }
    ]
    ```
    """
    return available_models
