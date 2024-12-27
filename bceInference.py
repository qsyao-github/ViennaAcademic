from BCEmbedding.tools.langchain import BCERerank
from langchain_experimental.text_splitter import SemanticChunker
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS

from langchain.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain.retrievers import ContextualCompressionRetriever

# init embedding model
embedding_model_name = 'maidalun1020/bce-embedding-base_v1'
# embedding_model_kwargs = {'device': 'cuda:0'}
embedding_encode_kwargs = {
    'batch_size': 100,
    'normalize_embeddings': True,
    'show_progress_bar': False
}

embed_model = HuggingFaceEmbeddings(model_name=embedding_model_name,
                                    encode_kwargs=embedding_encode_kwargs)

reranker_args = {'model': 'maidalun1020/bce-reranker-base_v1', 'top_n': 10}
reranker = BCERerank(**reranker_args)


# init documents
def get_splited_documents(file):
    documents = TextLoader(file).load()
    text_splitter = SemanticChunker(
        embed_model, sentence_split_regex=r"(?<=[.?!])\s*|(?<=[；。？！])")
    texts = text_splitter.split_documents(documents)
    return texts


# example 1. retrieval with embedding and reranker
def get_retriever(list_of_texts):
    total_texts = sum([i for i in list_of_texts], [])
    retriever = FAISS.from_documents(
        total_texts,
        embed_model,
        distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT).as_retriever(
            search_type="similarity",
            search_kwargs={
                "score_threshold": 0.35,
                "k": 5
            })
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=reranker, base_retriever=retriever)
    return compression_retriever


def get_response(query, compression_retriever):
    response = compression_retriever.get_relevant_documents(query)
    return response

