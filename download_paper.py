"""
下载Arxiv论文功能
"""

import concurrent.futures
import os
from typing import Literal, Tuple

from academic_search import search_arxiv
from agent_backend import agent_app
from docling_parser import parse_arxiv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from modelclient import deepseek_v3

translate_template = ChatPromptTemplate.from_messages(
    [
        ("system", "请将下列论文{type}译为中文，不要返回除{type}以外的其它内容"),
        ("user", "{content}"),
    ]
)


def get_arxiv_metadata(arxiv_id: str) -> Tuple[str, str, str]:
    """获取arxiv论文的标题、摘要和链接

    因为使用arxiv_id搜索，所以第一个一定是我们想要的论文

    Parameters
    ----------
    arxiv_id: str
        arxiv论文id

    Returns
    ----------
    Tuple[str, str, str]
        标题、摘要和链接
    """
    return next(search_arxiv(arxiv_id))


def translate_title(title: str) -> str:
    """翻译标题

    Parameters
    ----------
    title: str
        待翻译的标题

    Returns
    ----------
    str
        翻译后的标题
    """
    translate_title_prompt = translate_template.invoke(
        {"type": "标题", "content": title}
    )
    return deepseek_v3.invoke(translate_title_prompt).content


def translate_abstract(abstract: str) -> str:
    """翻译摘要

    Parameters
    ----------
    abstract: str
        待翻译的摘要

    Returns
    ----------
    str
        翻译后的摘要
    """
    translate_abstract_prompt = translate_template.invoke(
        {"type": "摘要", "content": abstract}
    )
    return deepseek_v3.invoke(translate_abstract_prompt).content


def process_concurrently(title: str, abstract: str, link: str) -> Tuple[str, str, str]:
    """并发执行翻译和解析任务

    翻译标题、摘要、docling解析。共3线程

    Parameters
    ----------
    title: str
        待翻译标题
    abstract: str
        待翻译摘要
    link: str
        arxiv论文链接

    Returns
    ----------
    Tuple[str, str, str]
        翻译后的标题、摘要和解析后的内容
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        title_future = executor.submit(translate_title, title)
        abstract_future = executor.submit(translate_abstract, abstract)
        content_future = executor.submit(parse_arxiv, link.replace("abs", "html"))
        return (
            title_future.result(),
            abstract_future.result(),
            content_future.result(),
        )


def update_conversation_thread(
    thread_id: str, message_content: str, message_type: Literal["user", "assistant"]
):
    """将标题、摘要加入对话

    由于在agent_backend.py中加入了对多模态信息的清洗，所以HumanMessage必须传入一个List[Dict[str, str]]。AIMessage只能传入字符串

    Parameters
    ----------
    thread_id: str
        对话id。为Gradio端的第一条信息的字符串形式，方便与其他对话区分
    message_content: str
        消息内容
    message_type: Literal["user", "assistant"]
        消息类型
    """
    if message_type == "user":
        MessageClass = HumanMessage
        content = [{"type": "text", "text": message_content}]
    else:
        MessageClass = AIMessage
        content = message_content
    agent_app.update_state(
        {"configurable": {"thread_id": thread_id}},
        {"messages": [MessageClass(content=content)]},
    )


def save_content(file_path: str, content: str):
    """将内容保存到文件

    Parameters
    ----------
    file_path: str
        文件路径
    content: str
        文件内容
    """
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def save_and_generate_response(
    title: str,
    abstract: str,
    translated_title: str,
    translated_abstract: str,
    content: str,
    save_dir: str,
) -> str:
    """保存论文内容并生成响应消息

    通过content是否为空处理docling解析失败的情况。写入文件的内容为解析后的内容或摘要(若解析失败)。

    Parameters
    ----------
    title: str
        原标题
    abstract: str
        原摘要
    translated_title: str
        翻译后的标题
    translated_abstract: str
        翻译后的摘要
    content: str
        解析后的内容。若解析失败，则为空字符串
    save_dir: str
        当前用户根目录

    Returns
    ----------
    str
        响应消息
    """
    save_path = os.path.join(save_dir, "knowledgeBase", f"{title}.md")
    save_content(save_path, content or abstract)

    if not content:
        return f"下载失败，请自行下载PDF并导入。\n\n标题：{translated_title}\n\n摘要：\n{translated_abstract}"
    return f"标题：{translated_title}\n\n摘要：\n{translated_abstract}"


def download_arxiv_paper(arxiv_id: str, current_dir: str) -> str:
    """下载并处理arXiv论文，返回翻译后的标题和摘要

    未找到论文的情况用try-except处理，报错信息不加入对话

    Parameters
    ----------
    arxiv_id: str
        arXiv论文id
    current_dir: str
        当前用户根目录

    Returns
    ----------
    str
        响应消息
    """

    # 获取论文元信息
    try:
        title, abstract, link = get_arxiv_metadata(arxiv_id)
    except Exception as e:
        return f"ID可能错误: {str(e)}"

    # 初始化消息和线程
    user_message = f"下载{arxiv_id}并翻译标题与摘要"
    thread_id = str(
        {"role": "user", "metadata": None, "content": user_message, "options": None}
    )
    update_conversation_thread(thread_id, user_message, "user")

    # 并行处理翻译和解析任务
    translated_title, translated_abstract, content = process_concurrently(
        title, abstract, link
    )

    # 保存论文内容并生成响应消息
    ai_message = save_and_generate_response(
        title, abstract, translated_title, translated_abstract, content, current_dir
    )

    # 更新对话线程并返回最终结果
    update_conversation_thread(thread_id, ai_message, "assistant")
    return ai_message
