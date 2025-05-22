import asyncio
import os
from contextlib import asynccontextmanager

import aiofiles
import magic
import uvloop
from chat_utils.agent_backend import close_conn, get_agent_app
from endpoint_utils import ALLOWED_IMAGE_TYPE, ALLOWED_PAPER_TYPE, respond_stream
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_agent_app()
    print("agent app loaded")
    yield
    await close_conn()


app = FastAPI(lifespan=lifespan)

app.mount("/media", StaticFiles(directory="media"), name="media")
app.mount("/documents", StaticFiles(directory="documents"), name="documents")


@app.post("/upload/image/{thread_id}")
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
    return {"url": final_path}


@app.post("/upload/document/{user}/paper")
async def upload_paper(file: UploadFile, user: str):
    # 类型验证
    chunk = await file.read(2048)

    detected_mime = magic.from_buffer(chunk, mime=True)
    if detected_mime not in ALLOWED_PAPER_TYPE:
        raise HTTPException(
            400,
            detail=f"Only plain text, html, xml, epub, json, rtf, docx, xlsx, pptx, odt, pdf are allowed. Got {detected_mime}",
        )
    await file.seek(0)

    # 异步流式上传
    final_path = os.path.join("documents", user, "paper", file.filename)
    async with aiofiles.open(final_path, "wb") as f:
        while chunk := await file.read(8192):
            await f.write(chunk)
    return {"url": final_path}


@app.post("/upload/document/{user}/code")
async def upload_code(file: UploadFile, user: str):
    # 类型验证
    chunk = await file.read(2048)

    detected_mime = magic.from_buffer(chunk, mime=True)
    if detected_mime != "text/plain":
        raise HTTPException(
            400,
            detail=f"Only plain text is allowed. Got {detected_mime}",
        )
    await file.seek(0)

    # 异步流式上传
    final_path = os.path.join("documents", user, "code", file.filename)
    async with aiofiles.open(final_path, "wb") as f:
        while chunk := await file.read(8192):
            await f.write(chunk)
    return {"url": final_path}


@app.post("/respond")
async def respond(query: str, thread_id: str, chat_mode: str, current_user: str):
    return StreamingResponse(respond_stream(query, thread_id, chat_mode, current_user))
