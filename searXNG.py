"""
SearXNG搜索引擎接口
"""

import re
from typing import List, Tuple

from langchain_community.utilities import SearxSearchWrapper

"""正则表达式，用于去除html标签"""
REMOVE_HTML_PATTERN = re.compile(r"<[^>]+>")
"""最多返回结果数。embedding模型召回100个文段，据此选择256"""
MAX_RESULTS = 256
academic_search_wrapper = SearxSearchWrapper(
    searx_host="http://localhost:8080", k=MAX_RESULTS
)


def searxng_websearch(query: str) -> List[Tuple[str, str, str]]:
    """SearXNG网页搜索

    仅返回前10结果

    Parameters
    ----------
    query: str
        搜索关键词

    Returns
    ----------
    List[Tuple[str, str, str]]
        搜索结果，标题、摘要和链接的元组
    """
    results = academic_search_wrapper.results(
        query,
        categories=["general"],
        num_results=10,
        language="all",
    )
    return [(result["title"], result["snippet"], result["link"]) for result in results]


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
        搜索结果，标题、摘要和链接的元组
    """
    results = academic_search_wrapper.results(
        query,
        categories=["science"],
        engines=[
            "arxiv",
            "crossref",
            "pubmed",
            "wikispecies",
            "openairedatasets",
            "openairepublications",
            "pbde",
        ],
        num_results=MAX_RESULTS,
        language="all",
    )
    return [
        (
            result["title"],
            REMOVE_HTML_PATTERN.sub("", result["snippet"]),
            result["link"],
        )
        for result in results
    ]
