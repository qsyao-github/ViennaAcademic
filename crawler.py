from typing import List

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

arxiv_browser_config = BrowserConfig(light_mode=True, text_mode=True)
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
arxiv_crawler = None


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
    global arxiv_crawler
    if arxiv_crawler is None:
        arxiv_crawler = AsyncWebCrawler(config=arxiv_browser_config)
        await arxiv_crawler.start()
    results = await arxiv_crawler.arun_many(urls, config=arxiv_crawler_config)
    return [result.markdown for result in results]


async def shutdown_arxiv_crawler():
    if arxiv_crawler is not None:
        await arxiv_crawler.close()
        print("arxiv crawler closed")
