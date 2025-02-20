from typing import List, Sequence, Optional
from langchain_core.embeddings import Embeddings
from langchain.retrievers.document_compressors.base import BaseDocumentCompressor
from langchain_core.documents import Document
from langchain.retrievers.document_compressors.base import BaseDocumentCompressor
from langchain.callbacks.manager import Callbacks
from modelclient import client5
import requests

def groupLists(lst: List[str]):
    # 将lst中每32个元素分为1组，最后一组可能不足32个元素
    grouped = [lst[i:i + 32] for i in range(0, len(lst), 32)]
    return grouped


def get_rerank(query, documents, top_n):
    url = "https://api.siliconflow.cn/v1/rerank"
    payload = {
        "model": "netease-youdao/bce-reranker-base_v1",
        "query": query,
        "documents": documents,
        "top_n": top_n,
        "return_documents": True
    }
    headers = {
        "Authorization":
        "Bearer",
        "Content-Type": "application/json"
    }
    response = requests.request("POST", url, json=payload,
                                headers=headers).json()

    return response["results"]


class CustomEmbeddings(Embeddings):

    def __init__(self, model: str):
        self.model = model

    def embed_query(self, text: str) -> List[float]:
        """Embed query text."""
        embedding = client1.embeddings.create(input=text, model=self.model)
        return embedding.data[0].embedding

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed search docs."""
        grouped = groupLists(texts)
        finalEmbedding = []
        for group in grouped:
            group = [text[:512] for text in group]
            embedding = client5.embeddings.create(input=group,
                                                  model=self.model)
            finalEmbedding.extend(
                [vector.embedding for vector in embedding.data])
        return finalEmbedding


class CustomCompressor(BaseDocumentCompressor):
    top_n: int = 3

    def __init__(self, top_n: int = 3):
        super().__init__(top_n=top_n)

    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Optional[Callbacks] = None
    ) -> Sequence[Document]:
        """
        Compress documents using `BCEmbedding RerankerModel API`.

        Args:
            documents: A sequence of documents to compress.
            query: The query to use for compressing the documents.
            callbacks: Callbacks to run during the compression process.

        Returns:
            A sequence of compressed documents.
        """
        if len(documents) == 0:  # to avoid empty api call
            return []
        doc_list = list(documents)

        passages = []
        valid_doc_list = []
        invalid_doc_list = []
        for d in doc_list:
            passage = d.page_content
            if isinstance(passage, str) and len(passage) > 0:
                passages.append(passage.replace('\n', ' '))
                valid_doc_list.append(d)
            else:
                invalid_doc_list.append(d)

        rerank_result = get_rerank(query, passages, self.top_n)

        final_results = []
        for item in rerank_result:
            score = item["relevance_score"]
            doc_id = item["index"]
            doc = valid_doc_list[doc_id]
            doc.metadata["relevance_score"] = score
            final_results.append(doc)
        for doc in invalid_doc_list:
            doc.metadata["relevance_score"] = 0
            final_results.append(doc)

        final_results = final_results[:self.top_n]
        return final_results

