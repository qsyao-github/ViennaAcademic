"""
自定义reranker实现
"""

import asyncio
from typing import Dict, List, Optional, Sequence, Tuple, Union

import aiohttp
import orjson
import uvloop
from langchain.callbacks.manager import Callbacks
from langchain.retrievers.document_compressors.base import BaseDocumentCompressor
from langchain_core.documents import Document
from private.api_keys import silicon_client_API_KEY, silicon_client_BASE_URL

BASE_URL = f"{silicon_client_BASE_URL}/"
HEADERS = {
    "Authorization": f"Bearer {silicon_client_API_KEY}",
    "Content-Type": "application/json",
}

"""全局reranker session"""
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
_reranker_session = None
_reranker_session_lock = asyncio.Lock()


async def get_rerank(
    query: str, documents: List[str], top_n: int
) -> List[Dict[str, Union[int, Dict[str, str]]]]:
    """异步获取rerank信息

    Parameters
    ----------
    query: str
        用户输入
    documents: List[str]
        文章片段
    top_n: int
        返回前top_n相关文段

    Returns
    ----------
    List[Dict[str, Union[int, Dict[str, str]]]]
        rerank结果
    """
    global _reranker_session, _reranker_session_lock
    async with _reranker_session_lock:
        if _reranker_session is None or _reranker_session.closed:
            connector = aiohttp.TCPConnector(
                limit_per_host=100,
                keepalive_timeout=120,
                ssl=False,
            )
            _reranker_session = aiohttp.ClientSession(
                base_url=BASE_URL,
                connector=connector,
                headers=HEADERS,
                json_serialize=lambda x: orjson.dumps(x).decode("utf-8"),
            )

    payload = {
        "model": "netease-youdao/bce-reranker-base_v1",
        "query": query,
        "documents": documents,
        "top_n": top_n,
        "return_documents": True,
    }

    try:
        # 发送请求（复用连接池）
        async with _reranker_session.post(
            "rerank",
            data=orjson.dumps(payload),
            timeout=aiohttp.ClientTimeout(total=10),
        ) as response:
            response.raise_for_status()
            return (await response.json()).get("results", [])

    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        print(f"Rerank Error: {type(e).__name__} - {str(e)}")
        return []


class CustomCompressor(BaseDocumentCompressor):
    """基于bce-reranker的自定义压缩器

    通过 BCE Reranker 模型对文档进行重排序，保留相关性最高的文档。

    Attributes
    ----------
    top_n: int = 100
        返回的文档数量上限(BCE 建议 rerank 返回5-10，默认保留更多结果)
    """

    top_n: int = 100

    def __init__(self, top_n: int = 100):
        """初始化压缩器

        Parameters
        ----------
        top_n: int = 100
            返回的文档数量上限(建议值：embedding召回50-100，rerank返回5-10)
        """
        super().__init__(top_n=top_n)

    def filter_documents(
        self, documents: Sequence[Document]
    ) -> Tuple[List[str], List[Document], List[Document]]:
        """过滤出包含有效文本内容的文档

        Parameters
        ----------
        documents: Sequence[Document]
            待过滤的文档列表

        Returns
        ----------
        Tuple[List[str], List[Document], List[Document]]
            有效文本内容列表，有效文档列表，无效文档列表
        """
        passages = []
        valid_doc_list = []
        invalid_doc_list = []
        for d in documents:
            if passage := d.page_content:
                passages.append(passage.replace("\n", " "))
                valid_doc_list.append(d)
            else:
                invalid_doc_list.append(d)
        return passages, valid_doc_list, invalid_doc_list

    def process_valid_docs(
        self,
        rerank_result: List[Dict[str, Union[int, Dict[str, str]]]],
        valid_doc_list: List[Document],
        final_results: List[Document],
    ) -> None:
        """处理有效文档

        为文档添加relevance_score和index字段，方便后续筛选

        Parameters
        ----------
        rerank_result: List[Dict[str, Union[int, Dict[str, str]]]]
            bce-reranker返回的结果
        valid_doc_list: List[Document]
            有效文档列表
        final_results: List[Document]
            最终结果列表。注入该函数的全局变量，该函数直接修改final_results
        """
        score_key = "relevance_score"
        index_key = "index"
        for item in rerank_result:
            score = item[score_key]
            doc_id = item[index_key]
            doc = valid_doc_list[doc_id]
            meta = doc.metadata
            meta[score_key] = score
            meta[index_key] = doc_id
            final_results.append(doc)

    def process_invalid_docs(
        self, invalid_doc_list: List[Document], final_results: List[Document]
    ) -> None:
        """处理无效文档

        Parameters
        ----------
        invalid_doc_list: List[Document]
            无效文档列表
        final_results: List[Document]
            最终结果列表。注入该函数的全局变量，该函数直接修改final_results
        """
        for doc in invalid_doc_list:
            doc.metadata["relevance_score"] = 0
            final_results.append(doc)

    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Optional[Callbacks] = None,
    ) -> Sequence[Document]:
        """
        用`BCEmbedding RerankerModel API`压缩文档

        这是同步版本，事件循环可能存在问题。前端应仅调用异步版本。

        Parameters
        ----------
        documents: Sequence[Document]
            一系列需要压缩的文档
        query: str
            用来压缩的用户输入
        callbacks: Optional[Callbacks] = None
            在压缩过程中运行的回调函数


        Returns
        ----------
        Sequence[Document]
            一系列压缩后的文档
        """
        if not documents:  # 避免API空调用
            return []
        doc_list = list(documents)
        passages, valid_doc_list, invalid_doc_list = self.filter_documents(doc_list)
        rerank_result = asyncio.run(get_rerank(query, passages, self.top_n))
        final_results = []
        self.process_valid_docs(rerank_result, valid_doc_list, final_results)
        self.process_invalid_docs(invalid_doc_list, final_results)
        return final_results

    async def acompress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Optional[Callbacks] = None,
    ) -> Sequence[Document]:
        """
        用`BCEmbedding RerankerModel API`压缩文档

        这是异步版本。前端应仅调用此版本。

        Parameters
        ----------
        documents: Sequence[Document]
            一系列需要压缩的文档
        query: str
            用来压缩的用户输入
        callbacks: Optional[Callbacks] = None
            在压缩过程中运行的回调函数


        Returns
        ----------
        Sequence[Document]
            一系列压缩后的文档
        """
        if not documents:  # 避免API空调用
            return []
        doc_list = list(documents)
        passages, valid_doc_list, invalid_doc_list = self.filter_documents(doc_list)
        rerank_result = await get_rerank(query, passages, self.top_n)
        final_results = []
        self.process_valid_docs(rerank_result, valid_doc_list, final_results)
        self.process_invalid_docs(invalid_doc_list, final_results)
        return final_results


async def shutdown_reranker_session():
    """释放reranker session"""
    global _reranker_session
    if _reranker_session and not _reranker_session.closed:
        await _reranker_session.close()
        _reranker_session = None
        print("reranker session closed")
