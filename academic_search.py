from langchain_community.retrievers import ArxivRetriever
from typing import Tuple, List
from searXNG import searxng_academic_search

retriever = ArxivRetriever()


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


from modelclient import bce_embedding_base
from typing import List
from custom_reranker import CustomCompressor
from langchain_community.vectorstores.faiss import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain.retrievers import ContextualCompressionRetriever

reranker = CustomCompressor(10)


def select_best_results(query: str) -> List[Tuple[str, str, str]]:
    results = searxng_academic_search(query)
    texts = [f"{item[0]}\n{item[1]}"[:512] for item in results]
    retriever = FAISS.from_texts(
        texts,
        bce_embedding_base,
        distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT,
    ).as_retriever(
        search_type="similarity",
        search_kwargs={"score_threshold": 0.35, "k": 100},
    )
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=reranker, base_retriever=retriever
    )
    response = compression_retriever.invoke(query)
    indicies = [int(item.metadata["index"]) for item in response]
    return [results[i] for i in indicies]
