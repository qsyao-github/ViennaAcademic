from typing import List

from crawl4ai import (
    AsyncWebCrawler,
    CrawlerRunConfig,
)
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

arxiv_crawler_config = CrawlerRunConfig(
    markdown_generator=DefaultMarkdownGenerator(
        options={
            "ignore_links": True,
            "ignore_images": True,
            "skip_internal_links": True,
            "escape_html": False,
        },
    ),
    css_selector="#main > div > article",
    excluded_tags=["button"],
)


async def crawl_arxivs(urls: List[str]) -> List[str]:
    """爬取arxiv论文的html网页，转换为markdown

    Parameters
    ----------
    urls: List[str]
        arxiv论文的html网页链接

    Returns
    ----------
    List[str]
        arxiv论文的markdown内容
    """
    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun_many(urls, config=arxiv_crawler_config)
        return [result.markdown for result in results]
