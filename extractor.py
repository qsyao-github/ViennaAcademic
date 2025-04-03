"""
WolframAlpha爬虫
"""

from typing import Dict, List

import orjson
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig
from crawl4ai.extraction_strategy import JsonXPathExtractionStrategy

"""WolframAlpha的爬虫规则"""
WOLFRAM_SCHEMA = {
    "name": "wolfram",
    "baseSelector": '//section[@tabindex="0"]',
    "fields": [
        {"name": "title", "selector": ".//span", "type": "text"},
        {
            "name": "content",
            "selector": ".//img[@alt]",
            "type": "attribute",
            "attribute": "alt",
        },
    ],
}
wolfram_browser_config = BrowserConfig(light_mode=True, text_mode=True)
wolfram_crawler = None
"""WolframAlpha的爬虫配置"""
wolfram_crawler_config = CrawlerRunConfig(
    extraction_strategy=JsonXPathExtractionStrategy(WOLFRAM_SCHEMA, verbose=True),
    wait_for="div.sc-a1dd50ea-0.LChfQ",
)


def process_wolfram_results(data: List[Dict]) -> str:
    """将爬取的json信息转换为markdown，去除图片信息

    Parameters
    ----------
    data: List[Dict]
        爬取的json信息

    Returns
    ----------
    str
        解析后的markdown
    """
    chunk_result = []
    for item in data:
        if (title := item.get("title", "")) and title != "图形":
            chunk_result.append(f"# {title}")
        if (content := item.get("content", "")) != "图形":
            chunk_result.append(content)
    return "\n".join(chunk_result)


async def get_wolfram(query: str) -> str:
    """爬取WolframAlpha的提示信息

    Parameters
    ----------
    query: str
        搜索词

    Returns
    ----------
    str
        爬取的提示信息
    """
    global wolfram_crawler
    if wolfram_crawler is None:
        wolfram_crawler = AsyncWebCrawler(config=wolfram_browser_config)
        await wolfram_crawler.start()
    url = f"https://www.wolframalpha.com/input?i={query}&lang=zh"
    result = await wolfram_crawler.arun(url, wolfram_crawler_config)
    if not result.success:
        return
    data = orjson.loads(result.extracted_content)
    return process_wolfram_results(data)


async def attach_hints(query: str) -> str:
    """在询问前附加WolframAlpha的提示信息

    Parameters
    ----------
    query: str
        搜索词

    Returns
    ----------
    query: str
        附加提示后的搜索词
    """
    if hints := await get_wolfram(query):
        query = f"Wolframalpha提示：\n```\n{hints}\n```\n{query}"
    return query


async def shutdown_wolfram_crawler():
    if wolfram_crawler is not None:
        await wolfram_crawler.close()
        print("wolfram crawler closed")
