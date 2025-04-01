"""
本地知识库实现

包括对上传、生成文件的分割向量化，embedding数据的本地储存，以及知识库文本召回
"""

import os
from typing import List, Union

from custom_reranker import CustomCompressor
from langchain.retrievers import ContextualCompressionRetriever
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_community.vectorstores.faiss import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_core.documents import Document
from modelclient import bce_embedding_base

reranker = CustomCompressor()
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
check_chars = frozenset(["。", "！", "？", ".", "!", "?"])
check_type = frozenset(["NarrativeText", "ListItem"])


async def get_document(file: str) -> List[Document]:
    """读取并分割文档

    按正则表达式分割为<=512字符的片段，避免超过bce-embedding上下文限制

    Parameters
    ----------
    file: str
        文件路径

    Returns
    ----------
    List[Document]
        文档片段列表
    """
    documents = await UnstructuredMarkdownLoader(file, mode="elements").aload()
    return text_splitter.split_documents(documents)


async def get_retriever(file: str) -> Union[FAISS, None]:
    """将本地文件向量化，返回召回器

    Parameters
    ----------
    file: str
        文件路径

    Returns
    ----------
    Union[FAISS, None]
        召回器。若文件为空，则返回None
    """
    if total_texts := await get_document(file):
        return await FAISS.afrom_documents(
            total_texts,
            bce_embedding_base,
            distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT,
        )


async def save_retriever(file: str, current_dir: str) -> None:
    """将召回器保存至本地

    Parameters
    ----------
    file: str
        文件名
    current_dir: str
        当前用户根目录
    """
    # 处理未知错误
    try:
        retriever = await get_retriever(f"{current_dir}/knowledgeBase/{file}.md")
        if retriever is not None:
            retriever.save_local(f"{current_dir}/retrievers", file)
    except Exception as e:
        print(f"An error occurred: {e}")


def remove_retriever(file: str, current_dir: str) -> None:
    """删除本地指定召回器

    Parameters
    ----------
    file: str
        文件名
    current_dir: str
        当前用户根目录
    """
    # 在demo.py中，由于文件删除键的渲染慢于IO，用户重复点击可导致报错，忽略
    retrievers_dir = os.path.join(current_dir, "retrievers")
    try:
        os.remove(
            os.path.join(retrievers_dir, f"{file}.pkl"),
        )
        os.remove(os.path.join(retrievers_dir, f"{file}.faiss"))
    except Exception as e:
        print(f"An error occurred: {e}")


async def update(current_dir: str) -> None:
    """更新知识库

    在上传、删除或程序生成文件后调用

    Parameters
    ----------
    current_dir: str
        当前用户根目录
    """
    knowledgeBase = {
        os.path.splitext(file)[0] for file in os.listdir(f"{current_dir}/knowledgeBase")
    }
    retrievers = {
        os.path.splitext(file)[0] for file in os.listdir(f"{current_dir}/retrievers")
    }
    # 保存上传、生成的文件
    for file in knowledgeBase - retrievers:
        await save_retriever(file, current_dir)
    # 移除已删除的文件
    for file in retrievers - knowledgeBase:
        remove_retriever(file, current_dir)


def merge_retrievers(current_dir: str) -> ContextualCompressionRetriever:
    """合并所有本地的召回器，并加入reranker精排，返回压缩召回器

    Parameters
    ----------
    current_dir: str
        当前用户根目录

    Returns
    ----------
    ContextualCompressionRetriever
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
        for file in {
            os.path.splitext(file)[0] for file in os.listdir(retriever_directory)
        }
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
    return ContextualCompressionRetriever(
        base_compressor=reranker, base_retriever=base_retriever
    )


def is_valid_document(category: str, content: str) -> bool:
    """判断文段是否满足要求

    Parameters
    ----------
    content: str
        文段

    Returns
    ----------
    bool
        非空，非标题，不含换行符且含句号，叹号，问号
    """
    return (
        content
        and category in check_type
        and any(char in content for char in check_chars)
    )


async def get_response(query: str, current_dir: str) -> str:
    """根据用户输入召回相关文段

    仅召回满足条件的前十，并进行排版

    Parameters
    ----------
    query: str
        用户输入
    current_dir: str
        当前用户根目录

    Returns
    ----------
    str
        相关文段
    """
    compression_retriever = merge_retrievers(current_dir)
    # 知识库为空的情况，提示用户与模型
    if compression_retriever is None:
        return "# 用户请注意，知识库为空。模型请根据自身理解尽量回答"
    response = await compression_retriever.ainvoke(query)
    text_response = []
    for document in response:
        content = document.page_content.strip()
        if not is_valid_document(document.metadata["category"], content):
            continue
        source = os.path.basename(document.metadata["source"])
        source = os.path.splitext(source)[0]
        text_response.append(f"{content} [Source: {source}]")
        if len(text_response) > 9:
            break
    return "\n\n".join(text_response)
