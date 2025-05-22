"""
下载Arxiv论文功能
"""

import asyncio
import os
from io import StringIO
from typing import AsyncGenerator

from chat_utils.agent_backend import get_agent_app
from langchain_core.messages import HumanMessage
from web_utils.academic_search import search_arxiv
from web_utils.arxiv_crawler import crawl_arxiv


async def download_arxiv_paper(
    arxiv_id: str, current_dir: str, for_user: bool = False, thread_id: str = ""
) -> AsyncGenerator[str, None]:
    """下载并处理arXiv论文，返回翻译后的标题和摘要

    未找到论文的情况用try-except处理，报错信息不加入对话。

    Parameters
    ----------
    arxiv_id: str
        arXiv论文id
    current_dir: str
        当前用户根目录

    Returns
    ----------
    str
        响应消息
    """
    try:
        title, abstract, link = next(await search_arxiv(arxiv_id))
    except Exception as e:
        yield f"ID可能错误: {str(e)}"
        return
    user_message = f"下载{arxiv_id}并翻译标题与摘要"
    thread_id = (
        thread_id
        if thread_id
        else str(
            {"role": "user", "metadata": None, "content": user_message, "options": None}
        )
    )
    arxiv_num = link.rsplit("/", 1)[-1]
    content_task = asyncio.create_task(crawl_arxiv(arxiv_num, current_dir, for_user))
    buffer = StringIO()
    if for_user:
        async for chunk, _ in (await get_agent_app()).astream(
            {
                "messages": [
                    HumanMessage(
                        content=[
                            {
                                "type": "text",
                                "text": f"请翻译标题与摘要\n\n{title}\n\n{abstract}",
                            }
                        ]
                    )
                ]
            },
            {"configurable": {"thread_id": thread_id, "mode": "常规", "now_time": ""}},
            stream_mode="messages",
        ):
            buffer.write(chunk.content)
            yield buffer.getvalue()
    else:
        yield ""
    content = await content_task
    with open(
        os.path.join(current_dir, "knowledgeBase", f"{title}.md"), "w", encoding="utf-8"
    ) as f:
        f.write(content or abstract)
    buffer.close()
