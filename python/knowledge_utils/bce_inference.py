"""
本地知识库实现

包括对上传、生成文件的分割向量化，embedding数据的本地储存，以及知识库文本召回
"""

import asyncio
import os

import aiofiles.os as aios
from langchain.retrievers import ContextualCompressionRetriever
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_community.vectorstores.faiss import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from python.knowledge_utils.custom_reranker import CustomCompressor
from python.llm_utils.modelclient import bce_embedding_base

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
        documents = await UnstructuredMarkdownLoader(
            f"{current_dir}/knowledgeBase/{file}.md", mode="elements"
        ).aload()
        if total_texts := text_splitter.split_documents(documents):
            retriever = await FAISS.afrom_documents(
                total_texts,
                bce_embedding_base,
                distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT,
            )
            retriever.save_local(f"{current_dir}/retrievers", file)
    except Exception as e:
        print(f"An error occurred: {e}")


async def remove_retriever(file: str, current_dir: str) -> None:
    retrievers_dir = os.path.join(current_dir, "retrievers")
    pkl_file = os.path.join(retrievers_dir, f"{file}.pkl")
    faiss_file = os.path.join(retrievers_dir, f"{file}.faiss")

    if await aios.path.exists(pkl_file):
        await aios.remove(pkl_file)
    if await aios.path.exists(faiss_file):
        await aios.remove(faiss_file)


async def update(current_dir: str) -> None:
    """更新知识库

    在上传、删除或程序生成文件后调用

    Parameters
    ----------
    current_dir: str
        当前用户根目录
    """
    knowledgeBase = {
        os.path.splitext(entry.name)[0]
        for entry in os.scandir(f"{current_dir}/knowledgeBase")
    }
    retrievers = {
        os.path.splitext(entry.name)[0]
        for entry in os.scandir(f"{current_dir}/retrievers")
    }
    # 保存上传、生成的文件
    save_tasks = [
        save_retriever(file, current_dir) for file in knowledgeBase - retrievers
    ]
    remove_tasks = [
        remove_retriever(file, current_dir) for file in retrievers - knowledgeBase
    ]
    await asyncio.gather(*save_tasks, *remove_tasks)


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
            os.path.splitext(entry.name)[0] for entry in os.scandir(retriever_directory)
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
        source = os.path.splitext(os.path.basename(document.metadata["source"]))[0]
        text_response.append(f"{content} [Source: {source}]")
        if len(text_response) > 9:
            break
    return "\n\n".join(text_response)
