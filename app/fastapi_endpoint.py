"""
运行：
uvicorn fastapi_endpoint:app --host 0.0.0.0 --port 8000 --loop uvloop
"""

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Annotated, Literal

import aiofiles
import magic
import uvloop
from auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    Token,
    User,
    authenticate_user,
    create_access_token,
    create_user,
    get_current_user,
)
from chat_utils.agent_backend import (
    ENABLE_REASONING,
    ENABLE_TOOL,
    MULTIMODAL,
    close_conn,
    get_agent_app,
    models,
)
from endpoint_utils import ALLOWED_IMAGE_TYPE, ALLOWED_PAPER_TYPE, respond_stream
from fastapi import Depends, FastAPI, HTTPException, UploadFile, status
from fastapi.responses import ORJSONResponse, PlainTextResponse, StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# from file_utils.file_conversion import everything_to_markdown

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_agent_app()
    yield
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


@app.post("/register", response_class=PlainTextResponse)
async def register(username: str, password: str):
    """
    注册新用户
    """
    return await create_user(username, password)


# 文件系统


@app.post("/upload/image/{thread_id}", response_class=PlainTextResponse)
async def upload_image(
    file: UploadFile, thread_id: str, _user: Annotated[User, Depends(get_current_user)]
):
    """
    在{thread_id}对话中上传图片

    示例输出：
    ```json
    "/media/somethread_imagename"
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
    final_path = os.path.join("media", f"{thread_id}_{file.filename}")
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
    final_path = os.path.join("documents", user.username, "paper", file.filename)

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
        knowledgeBase_path = os.path.join("documents", user, "knowledgeBase")
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
    final_path = os.path.join("documents", user.username, "code", file.filename)
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


# 模型回复


class ChatQuery(BaseModel):
    query: str
    image_urls: list[str]
    file_urls: list[str]
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
            "/media/code_generated_image.png"
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

    Notes
    ----------
    1. 当前可用的模型列表中未能找到模型名称和模型类型匹配的模型，返回{"ERROR": "No such model"}{"image_urls": []}
    2. 正常返回片段有
        - {"content": "正文片段"}
        - {"tool_calls": "工具调用json字符串片段"}
        - {"reasoning_content": "推理片段"}
        - {"image_urls": ["/path/to/model/generated/image_1", "/path/to/model/generated/image_2"]}
    3. 返回上述json的字节流，需前端实现处理各种类型回复以及增量更新的逻辑
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
            chat_query.enable_tool,
            chat_query.enable_thinking,
            chat_query.multimodal,
        ),
    )


@app.get("/models")
async def get_model_list():
    """
    获取当且可用的模型及其类型

    示例输出：
    ```json
    [
        {
            "model_name": "deepseek-v3",
            "enable_tool": false,
            "enable_reasoning": false,
            "multimodal": false
        },
        {
            "model_name": "deepseek-v3",
            "enable_tool": true,
            "enable_reasoning": false,
            "multimodal": false
        },
    ]
    ```
    """
    return [
        {
            "model_name": model[2],
            "enable_tool": bool(model[1] & ENABLE_TOOL),
            "enable_reasoning": bool(model[1] & ENABLE_REASONING),
            "multimodal": bool(model[1] & MULTIMODAL),
        }
        for model in models
    ]
