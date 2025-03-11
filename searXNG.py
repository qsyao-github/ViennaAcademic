from langchain_community.utilities import SearxSearchWrapper
from typing import Tuple, List
import re

academic_search_wrapper = SearxSearchWrapper(searx_host="http://localhost:8080", k=256)

def searxng_websearch(query: str) -> List[Tuple[str, str, str]]:
    results = academic_search_wrapper.results(
        query,
        categories=["general"],
        num_results=10,
        language="all",
    )
    return [(result["title"], result["snippet"], result["link"]) for result in results]

REMOVE_XML_PATTERN = re.compile(r'<[^>]+>')


# 定义一个函数，用于进行学术搜索
def searxng_academic_search(query: str) -> List[Tuple[str, str, str]]:
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
        num_results=256,
        language="all",
    )
    return [(result["title"], REMOVE_XML_PATTERN.sub('', result["snippet"]), result["link"]) for result in results]
