"""
下载Arxiv论文功能
"""

import asyncio
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


async def get_arxiv_metadata(arxiv_id: str) -> Tuple[str, str, str]:
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
    return next(await search_arxiv(arxiv_id))


async def translate_title(title: str) -> str:
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
    translate_title_prompt = await translate_template.ainvoke(
        {"type": "标题", "content": title}
    )
    return (await deepseek_v3.ainvoke(translate_title_prompt)).content


async def translate_abstract(abstract: str) -> str:
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
    translate_abstract_prompt = await translate_template.ainvoke(
        {"type": "摘要", "content": abstract}
    )
    return (await deepseek_v3.ainvoke(translate_abstract_prompt)).content


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


def generate_response(
    translated_title: str,
    translated_abstract: str,
    content: str,
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
    if not content:
        return f"下载失败，请自行下载PDF并导入。\n\n标题：{translated_title}\n\n摘要：\n{translated_abstract}"
    return f"标题：{translated_title}\n\n摘要：\n{translated_abstract}"


async def download_arxiv_paper(arxiv_id: str, current_dir: str) -> str:
    """下载并处理arXiv论文，返回翻译后的标题和摘要

    未找到论文的情况用try-except处理，报错信息不加入对话。

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

    Notes
    ----------
    并行逻辑：
    ```mermaid
    graph TD
    Start[开始] --> A[获取arXiv元数据]
    A --> B[创建用户消息和thread_id]
    B --> C1[启动翻译标题任务]
    B --> C2[启动翻译摘要任务]
    B --> C3[启动更新用户消息任务]
    B --> D[解析arXiv内容]
    D --> E[启动保存内容任务]
    C1 --> F[翻译标题完成]
    C2 --> G[翻译摘要完成]
    C3 --> H[更新用户消息完成]
    F & G & H --> I[生成响应]
    I --> J[更新AI消息]
    E --> K[保存内容完成]
    J & K --> L[返回响应]
    ```
    """
    try:
        title, abstract, link = await get_arxiv_metadata(arxiv_id)
    except Exception as e:
        return f"ID可能错误: {str(e)}"
    user_message = f"下载{arxiv_id}并翻译标题与摘要"
    thread_id = str(
        {"role": "user", "metadata": None, "content": user_message, "options": None}
    )
    translate_title_task = asyncio.create_task(translate_title(title))
    translate_abstract_task = asyncio.create_task(translate_abstract(abstract))
    content = parse_arxiv(link.replace("abs", "html").replace("http://", "https://"))
    save_content(
        os.path.join(current_dir, "knowledgeBase", f"{title}.md"),
        content or abstract,
    )
    update_conversation_thread(thread_id, user_message, "user")
    translated_title = await translate_title_task
    translated_abstract = await translate_abstract_task
    ai_message = generate_response(translated_title, translated_abstract, content)
    update_conversation_thread(thread_id, ai_message, "assistant")
    return ai_message
