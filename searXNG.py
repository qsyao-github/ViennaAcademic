"""
SearXNG搜索引擎接口
"""

from typing import Generator, List, Tuple

from langchain_community.utilities import SearxSearchWrapper

"""最多返回结果数。embedding模型召回100个文段，据此选择256"""
MAX_RESULTS = 256
academic_search_wrapper = SearxSearchWrapper(
    searx_host="http://localhost:8080", k=MAX_RESULTS, unsecure=True
)


def searxng_websearch(query: str) -> Generator[Tuple[str, str, str], None, None]:
    """SearXNG网页搜索

    仅返回前10结果

    Parameters
    ----------
    query: str
        搜索关键词

    Returns
    ----------
    Generator[Tuple[str, str, str], None, None]
        搜索结果，标题、摘要和链接生成器
    """
    results = academic_search_wrapper.results(
        query,
        categories=["general"],
        num_results=10,
        language="all",
    )
    return ((result["title"], result["snippet"], result["link"]) for result in results)


def searxng_academic_search(query: str) -> List[Tuple[str, str, str]]:
    """SearXNG学术搜索

    crossref搜索结果可能包含html标签，需要去除

    Parameters
    ----------
    query: str
        搜索关键词

    Returns
    ----------
    List[Tuple[str, str, str]]
        搜索结果，标题、摘要和链接列表。因后续需要按元素访问，不能使用生成器
    """
    results = academic_search_wrapper.results(
        query,
        categories=["science"],
        engines=["arxiv", "google_scholar", "pubmed"],
        num_results=MAX_RESULTS,
        language="all",
    )
    return [(result["title"], result["snippet"], result["link"]) for result in results]
