"""
WolframAlpha爬虫
"""

import asyncio
import orjson

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
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


async def get_wolfram(query: str) -> str:
    config = CrawlerRunConfig(
        extraction_strategy=JsonXPathExtractionStrategy(WOLFRAM_SCHEMA, verbose=True),
        wait_for="div.sc-a1dd50ea-0.LChfQ",
    )
    url = f"https://www.wolframalpha.com/input?i={query}&lang=zh"
    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(url, config)
        if not result.success:
            return
        data = orjson.loads(result.extracted_content)
        chunk_result = []
        for item in data:
            if (title := item.get("title", "")) and title != "图形":
                chunk_result.append(f"# {title}")
            if (content := item.get("content", "")) != "图形":
                chunk_result.append(content)
        return "\n".join(chunk_result)


def attach_hints(query: str) -> str:
    if hints := asyncio.run(get_wolfram(query)):
        query = f"Wolframalpha提示：\n```\n{hints}\n```\n{query}"
    return query
