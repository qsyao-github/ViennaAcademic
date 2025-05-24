"""
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
from chat_utils.agent_backend import close_conn, get_agent_app
from endpoint_utils import ALLOWED_IMAGE_TYPE, ALLOWED_PAPER_TYPE, respond_stream
from fastapi import Depends, FastAPI, HTTPException, UploadFile, status
from fastapi.responses import ORJSONResponse, PlainTextResponse, StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles

# from file_utils.file_conversion import everything_to_markdown
from pydantic import BaseModel

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
    return await create_user(username, password)


# 文件系统


@app.post("/upload/image/{thread_id}", response_class=PlainTextResponse)
async def upload_image(file: UploadFile, thread_id: str):
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


""" @app.post("/upload/document/paper", response_class=PlainTextResponse)
async def upload_paper(
    file: UploadFile, user: Annotated[User, Depends(get_current_user)]
):
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
    return f"/{final_path}" """


@app.post("/upload/document/code", response_class=PlainTextResponse)
async def upload_code(
    file: UploadFile, user: Annotated[User, Depends(get_current_user)]
):
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
    dir_path = os.path.join("documents", user.username, directory)
    return [entry.name for entry in os.scandir(dir_path)]


# 模型回复


class ChatQuery(BaseModel):
    query: str
    image_urls: list[str]
    chat_mode: Literal["常规", "工具", "多模态", "知识库", "网页搜索"]


@app.post("/chat/{thread_id}")
async def respond(
    thread_id: str,
    chat_query: ChatQuery,
    current_user: Annotated[User, Depends(get_current_user)],
):
    return StreamingResponse(
        respond_stream(
            chat_query.query,
            chat_query.image_urls,
            thread_id,
            chat_query.chat_mode,
            current_user.username,
        ),
    )
