from langchain_community.utilities import SearxSearchWrapper
from typing import Tuple, List

academic_search_wrapper = SearxSearchWrapper(searx_host="http://localhost:8080")

def searxng_websearch(query: str) -> List[Tuple[str, str, str]]:
    results = academic_search_wrapper.results(
        "Risch Algorithm",
        categories=["general"],
        num_results=10,
        language="all",
    )
    return [(result["title"], result["snippet"], result["link"]) for result in results]
