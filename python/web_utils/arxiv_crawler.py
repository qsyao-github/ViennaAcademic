"""
arxiv爬虫
"""

import asyncio
import os

import aiofiles
import aiohttp
import pymupdf4llm
from lxml import etree
from markdownify import markdownify as md
from va_rust_utils import web_utils_arxiv_crawler_process_markdown as process_markdown
from python.file_utils.file_conversion import everything_to_markdown

"""全局session"""
_arxiv_session = None
_arxiv_session_lock = asyncio.Lock()


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0"
}


async def process_pdf_arxiv(
    arxiv_num: str, current_dir: str, for_user: bool = False
) -> str:
    """下载pdf并解析为markdown

    Parameters
    ----------
    arxiv_num: str
        arxiv编号
    current_dir: str
        用户根目录

    Returns
    ----------
    str
        markdown内容，出现错误返回空字符串
    """
    global _arxiv_session
    try:
        pdf_path = f"{current_dir}/paper/{arxiv_num}.pdf"
        if os.path.exists(pdf_path) and for_user:
            return everything_to_markdown(pdf_path, f"{current_dir}/knowledgeBase")
        async with _arxiv_session.get(f"pdf/{arxiv_num}") as response:
            response.raise_for_status()

            async with aiofiles.open(f"{current_dir}/paper/{arxiv_num}.pdf", "wb") as f:
                async for chunk in response.content.iter_chunked(256 * 1024):
                    await f.write(chunk)
        if for_user:
            return everything_to_markdown(pdf_path, f"{current_dir}/knowledgeBase")
        result = pymupdf4llm.to_markdown(pdf_path)
        os.remove(pdf_path)
        return result
    except Exception as e:
        print(e)
        return ""


async def crawl_arxiv(arxiv_num: str, current_dir: str, for_user: bool = False) -> str:
    """爬取arxiv

    Parameters
    ----------
    arxiv_num: str
        arxiv编号
    current_dir: str
        用户根目录

    Returns
    ----------
    str
        markdown内容，出现错误返回空字符串

    Notes
    ----------
    当arxiv提供了html格式时，优先解析html。若不提供，则异步下载pdf并解析
    """
    global _arxiv_session
    async with _arxiv_session_lock:
        if _arxiv_session is None or _arxiv_session.closed:
            connector = aiohttp.TCPConnector(
                limit_per_host=100,
                keepalive_timeout=120,
                ssl=False,
            )
            timeout = aiohttp.ClientTimeout(connect=10, sock_read=20)
            _arxiv_session = aiohttp.ClientSession(
                base_url="https://arxiv.org",
                connector=connector,
                headers=HEADERS,
                timeout=timeout,
            )
    async with _arxiv_session.get(f"html/{arxiv_num}") as response:
        if response.status == 404:
            return await process_pdf_arxiv(arxiv_num, current_dir, for_user)
        html = await response.text()

    parser = etree.HTMLParser(remove_comments=True, encoding="utf-8")
    tree = etree.fromstring(html, parser)

    article_node = tree.xpath(
        '//*[@id="main"]/div/article | /html/body/div[1]/div/article'
    )

    if not article_node:
        return await process_pdf_arxiv(arxiv_num, current_dir, for_user)

    target_html = etree.tostring(
        article_node[0], encoding="unicode", method="html", pretty_print=True
    )
    markdown_content = md(
        target_html,
        heading_style="ATX",  # 使用#标题
        code_language="latex",  # 识别代码块语言
        auto_links=False,
        escape_asterisks=False,
        escape_underscores=False,
        escape_misc=False,
        strip=["img", "button"],
    )
    return process_markdown(markdown_content)


async def shutdown_arxiv_session():
    """关闭arxiv session"""
    global _arxiv_session
    if _arxiv_session and not _arxiv_session.closed:
        await _arxiv_session.close()
        _arxiv_session = None
        print("arxiv session closed")
