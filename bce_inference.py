import os
from typing import List

from langchain_community.vectorstores.faiss import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain.retrievers import ContextualCompressionRetriever
from langchain.text_splitter import RecursiveCharacterTextSplitter

from custom_reranker import CustomCompressor
from modelclient import bce_embedding_base

reranker = CustomCompressor(10)
text_splitter = RecursiveCharacterTextSplitter(
    separators=[
        r"\n{2,}",
        r"\n+",
        r"\s{2,}",
        r"(?<=[.!?;])\s+|(?<=[。？！；])",
        r"(?<=[,])\s+|(?<=[，])",
        r"\s+",
    ],
    is_separator_regex=True,
    chunk_overlap=16,
    chunk_size=512,
)
check_chars = ["。", "！", "？", ".", "!", "?"]


def get_document(file: str) -> List[Document]:
    """读取文档，按正则表达式分割为<=512字符的片段，避免超过bce-embedding上下文限制

    Args:
        file: 文件路径

    Returns:
        文档片段列表
    """
    documents = TextLoader(file).load()
    texts = text_splitter.split_documents(documents)
    return texts


def get_retriever(file: str) -> FAISS:
    """将本地文件向量化，返回召回器

    Args:
        file: 文件路径

    Returns:
        召回器
    """
    total_texts = get_document(file)
    if total_texts:
        retriever = FAISS.from_documents(
            total_texts,
            bce_embedding_base,
            distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT,
        )
        return retriever


def save_retriever(file: str, current_dir: str) -> None:
    """将召回器保存至本地

    Args:
        file: 文件名
        current_dir: 当前用户根目录
    """
    # 当文件为空将会产生报错，忽略
    try:
        retriever = get_retriever(f"{current_dir}/knowledgeBase/{file}.md")
        if retriever is not None:
            retriever.save_local(f"{current_dir}/retrievers", file)
    except:
        pass


def remove_retriever(file: str, current_dir: str) -> None:
    """删除本地指定召回器

    Args:
        file: 文件名
        current_dir: 当前用户根目录
    """
    # 在demo.py中，由于文件删除键的渲染慢于IO，用户重复点击可导致报错，忽略
    try:
        os.remove(f"{current_dir}/retrievers/{file}.pkl")
        os.remove(f"{current_dir}/retrievers/{file}.faiss")
    except:
        pass


def update(current_dir: str) -> None:
    """当上传、删除或程序生成文件后，更新知识库

    Args:
        current_dir: 当前用户根目录
    """
    knowledgeBase = set(
        os.path.splitext(file)[0] for file in os.listdir(f"{current_dir}/knowledgeBase")
    )
    retrievers = set(
        os.path.splitext(file)[0] for file in os.listdir(f"{current_dir}/retrievers")
    )
    # 保存上传、生成的文件
    for file in knowledgeBase - retrievers:
        save_retriever(file, current_dir)
    # 移除已删除的文件
    for file in retrievers - knowledgeBase:
        remove_retriever(file, current_dir)


def merge_retrievers(current_dir: str) -> ContextualCompressionRetriever:
    """合并所有本地的召回器，并加入reranker精排，返回压缩召回器

    Args:
        current_dir: 当前用户根目录

    Returns:
        所有文件的压缩召回器
    """
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
    # 知识库为空的情况，将会在get_response处理
    if not retrievers:
        return None
    base_retriever = retrievers.pop()
    for retriever in retrievers:
        base_retriever.merge_from(retriever)
    base_retriever = base_retriever.as_retriever(
        search_type="similarity",
        search_kwargs={"score_threshold": 0.35, "k": 100},
    )
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=reranker, base_retriever=base_retriever
    )
    return compression_retriever


def get_response(query: str, current_dir: str) -> str:
    """根据用户输入召回相关文段

    Args:
        query: 用户输入
        current_dir: 当前用户根目录

    Returns:
        相关文段
    """
    compression_retriever = merge_retrievers(current_dir)
    # 知识库为空的情况，提示用户与模型
    if compression_retriever is None:
        return "# 用户请注意，知识库为空。模型请根据自身理解尽量回答"
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
