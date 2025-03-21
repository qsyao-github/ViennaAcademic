from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CrawlerMonitor, BrowserConfig, DisplayMode, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.async_dispatcher import MemoryAdaptiveDispatcher

browser_config = BrowserConfig(headless=True, verbose=False)
config = CrawlerRunConfig(
    markdown_generator=DefaultMarkdownGenerator(
        content_filter=PruningContentFilter(threshold=0.4,
                                            threshold_type="dynamic"),
        options={
            "ignore_links": True,
            "ignore_images": True,
            "skip_internal_links": True,
            "escape_html": False
        }),
    stream=True,
    excluded_tags=['form', 'header', "nav", "footer"],
    exclude_external_links=True,

    # Content processing
    process_iframes=True,
    remove_overlay_elements=True,

    # Cache control
    cache_mode=CacheMode.ENABLED)
dispatcher = MemoryAdaptiveDispatcher(
    memory_threshold_percent=70.0,
    check_interval=1.0,
    max_session_permit=10,
    monitor=CrawlerMonitor(display_mode=DisplayMode.DETAILED))


async def crawl_url(urls):
    async with AsyncWebCrawler(config=browser_config) as crawler:
        async for result in await crawler.arun_many(urls=urls,
                                                    config=config,
                                                    dispatcher=dispatcher):
            if result.success:
                print(result.url)
                print(result.html)
