from typing import Tuple, List

from langchain_community.retrievers import ArxivRetriever
from langchain_community.vectorstores.faiss import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain.retrievers import ContextualCompressionRetriever

from custom_reranker import CustomCompressor
from modelclient import bce_embedding_base
from searXNG import searxng_academic_search

retriever = ArxivRetriever()
reranker = CustomCompressor(10)


def search_arxiv(query: str) -> List[Tuple[str, str, str]]:
    """搜索arxiv论文，返回标题、摘要和链接

    Args:
        query: Arxiv ID或搜索关键词

    Returns:
        (标题, 摘要, 链接)元组组成的列表
    """
    docs = retriever.invoke(query)
    return [
        (
            doc.metadata["Title"],
            doc.page_content.replace("\n", " "),
            doc.metadata["Entry ID"],
        )
        for doc in docs
    ]


def select_academic_search_result(query: str) -> List[Tuple[str, str, str]]:
    """使用searxng获取学术搜索结果，并使用bce embedding+rerank召回相关性>=0.35的前十结果

    Args:
        query: 搜索关键词

    Returns:
        (标题, 摘要, 链接)元组组成的列表
    """
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
