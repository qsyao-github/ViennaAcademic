from modelclient import bce_embedding_base
from typing import List
from langchain_core.documents import Document
from custom_reranker import CustomCompressor
from langchain_community.vectorstores.faiss import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.retrievers import ContextualCompressionRetriever
import os

reranker = CustomCompressor(10)
text_splitter = RecursiveCharacterTextSplitter(
    separators=[
    r"\n{2,}", r"\n+", r"\s{2,}", r"(?<=[.!?;])\s+|(?<=[。？！；])",
    r"(?<=[,])\s+|(?<=[，])", r"\s+"
],
    is_separator_regex=True,
    chunk_overlap=16,
    chunk_size=512,
)
check_chars = ["。", "！", "？", ".", "!", "?"]


def get_document(file: str) -> List[Document]:
    documents = TextLoader(file).load()
    texts = text_splitter.split_documents(documents)
    return texts


def get_retriever(file: str) -> FAISS:
    total_texts = get_document(file)
    if total_texts:
        retriever = FAISS.from_documents(
            total_texts,
            bce_embedding_base,
            distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT,
        )
        return retriever


def save_retriever(file: str, current_dir: str) -> None:
    # try:
    retriever = get_retriever(f"{current_dir}/knowledgeBase/{file}.md")
    if retriever is not None:
        retriever.save_local(f"{current_dir}/retrievers", file)
    # except:
        # pass


def remove_retriever(file: str, current_dir: str) -> None:
    try:
        os.remove(f"{current_dir}/retrievers/{file}.pkl")
        os.remove(f"{current_dir}/retrievers/{file}.faiss")
    except:
        pass


def update(current_dir: str) -> None:
    print(current_dir)
    knowledgeBase = set(
        os.path.splitext(file)[0] for file in os.listdir(f"{current_dir}/knowledgeBase")
    )
    retrievers = set(
        os.path.splitext(file)[0] for file in os.listdir(f"{current_dir}/retrievers")
    )
    print(knowledgeBase)
    print(retrievers)
    for file in knowledgeBase - retrievers:
        save_retriever(file, current_dir)
    for file in retrievers - knowledgeBase:
        remove_retriever(file, current_dir)


def merge_retrievers(current_dir: str) -> ContextualCompressionRetriever:
    retriever_directory = f"{current_dir}/retrievers"
    retrievers = [
        FAISS.load_local(
            retriever_directory,
            bce_embedding_base,
            file,
            distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT,
            allow_dangerous_deserialization=True,
        )
        for file in set(
            os.path.splitext(file)[0] for file in os.listdir(retriever_directory)
        )
    ]
    base_retriever = retrievers.pop()
    for retriever in retrievers:
        base_retriever.merge_from(retriever)
    base_retriever = base_retriever.as_retriever(
        search_type="similarity",
        search_kwargs={"score_threshold": 0.35, "k": 100, "fetch-k": 100},
    )
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=reranker, base_retriever=base_retriever
    )
    return compression_retriever


def get_response(query: str, current_dir: str) -> str:
    compression_retriever = merge_retrievers(current_dir)
    response = compression_retriever.invoke(query)
    text_response = []
    for document in response:
        indicator = "Source: "
        content = document.page_content.strip()
        if (
            content
            and "#" not in content
            and "\n" not in content
            and any(char in content for char in check_chars)
            and document.metadata["relevance_score"] >= 0.35
        ):
            source = os.path.basename(document.metadata["source"])
            if source.startswith("STORMtemp"):
                source = source[9:]
                indicator = "Number: "
            source = os.path.splitext(source)[0]
            text_response.append(f"{content} [{indicator}{source}]")
    return "\n\n".join(text_response)
