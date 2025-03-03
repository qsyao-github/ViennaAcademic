import requests
from typing import List, Sequence, Optional, Dict, Union
from langchain_core.documents import Document
from modelclient import silicon_client_API_KEY, silicon_client_BASE_URL
from langchain.retrievers.document_compressors.base import BaseDocumentCompressor
from langchain.callbacks.manager import Callbacks

url = silicon_client_BASE_URL + '/rerank'
headers = {
    "Authorization": f"Bearer {silicon_client_API_KEY}",
    "Content-Type": "application/json"
}


def get_rerank(query: str, documents: List[str],
               top_n: int) -> List[Dict[str, Union[int, Dict[str, str]]]]:

    payload = {
        "model": "netease-youdao/bce-reranker-base_v1",
        "query": query,
        "documents": documents,
        "top_n": top_n,
        "return_documents": True
    }

    response = requests.request("POST", url, json=payload,
                                headers=headers).json()

    return response["results"]


class CustomCompressor(BaseDocumentCompressor):
    top_n: int = 3

    def __init__(self, top_n: int = 3):
        super().__init__(top_n=top_n)

    def compress_documents(
            self,
            documents: Sequence[Document],
            query: str,
            callbacks: Optional[Callbacks] = None) -> Sequence[Document]:
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
