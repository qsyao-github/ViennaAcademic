"""
提供Arxiv和SearXNG学术搜索的最高级API
"""

from typing import Generator, Tuple

from knowledge_utils.custom_reranker import CustomCompressor
from langchain.retrievers import ContextualCompressionRetriever
from langchain_community.retrievers import ArxivRetriever
from langchain_community.vectorstores.faiss import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from llm_utils.modelclient import bce_embedding_base
from .searXNG import searxng_academic_search

retriever = ArxivRetriever()
reranker = CustomCompressor()


async def search_arxiv(query: str) -> Generator[Tuple[str, str, str], None, None]:
    """搜索arxiv论文

    Parameters
    ----------
    query: str
        Arxiv ID或搜索关键词

    Returns
    ----------
    Generator[Tuple[str, str, str], None, None]
        (标题, 摘要, 链接)元组生成器
    """
    docs = await retriever.ainvoke(query)
    return (
        (
            doc.metadata["Title"],
            doc.page_content.replace("\n", " "),
            doc.metadata["Entry ID"],
        )
        for doc in docs
    )


async def select_academic_search_result(
    query: str,
) -> Generator[Tuple[str, str, str], None, None]:
    """使用searxng获取学术搜索结果

    bce embedding+rerank召回相关性>=0.35的结果

    Parameters
    ----------
    query: str
        搜索关键词

    Returns
    ----------
    Generator[Tuple[str, str, str]]
        (标题, 摘要, 链接)元组生成器
    """
    results = await searxng_academic_search(query)
    if not results:
        return
    # 截取前512字符，防止超过bce-embedding上下文限制
    texts = [f"{item[0]}\n{item[1]}"[:512] for item in results]
    # 召回100个文段，要求相关分数大于0.35
    retriever = (
        await FAISS.afrom_texts(
            texts,
            bce_embedding_base,
            distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT,
        )
    ).as_retriever(
        search_type="similarity",
        search_kwargs={"score_threshold": 0.35, "k": 100},
    )
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=reranker, base_retriever=retriever
    )
    response = await compression_retriever.ainvoke(query)
    indicies = (int(item.metadata["index"]) for item in response)
    return (results[i] for i in indicies)
