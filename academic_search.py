from langchain_community.retrievers import ArxivRetriever
from habanero import Crossref
from typing import Tuple, List
import re

retriever = ArxivRetriever()
cr = Crossref(timeout=30)
CROSSREF_ABSTRACT_PATTERN = re.compile(r"<jats:p>(.*?)</jats:p>")


def search_arxiv(query: str) -> List[Tuple[str, str, str]]:
    docs = retriever.invoke(query)
    return [
        (
            doc.metadata["Title"],
            doc.page_content.replace("\n", " "),
            doc.metadata["Entry ID"],
        )
        for doc in docs
    ]


def search_crossref(query: str) -> List[Tuple[str, str, str]]:
    x = cr.works(query=query)
    return [
        (
            item.get("title", "")[0],
            CROSSREF_ABSTRACT_PATTERN.search(
                item.get("abstract", "<jats:p></jats:p>")
            ).group(1),
            item.get("URL", ""),
        )
        for item in x["message"]["items"]
    ]
