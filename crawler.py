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


async def crawl_arxivs(urls):
    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun_many(urls, config=arxiv_crawler_config)
        return [result.markdown for result in results]
