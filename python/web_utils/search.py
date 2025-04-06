"""
搜索功能与前端的接口
"""

from io import StringIO
from typing import AsyncGenerator, Callable, Generator, Iterator, List, Tuple

from langchain_core.prompts import ChatPromptTemplate
from python.llm_utils.modelclient import deepseek_v3
from python.llm_utils.system_prompt import ACADEMIC_SEARCH
from python.web_utils.academic_search import select_academic_search_result
from python.web_utils.searXNG import searxng_websearch

generate_summary_prompt_tempate = ChatPromptTemplate.from_messages(
    [
        ("system", ACADEMIC_SEARCH),
        ("user", "{content}"),
    ]
)


SearchResult = Tuple[str, str, str]  # (title, snippet, link)
SearchFunction = Callable[[str], Generator[SearchResult, None, None]]

# 格式字符串常量
RESULT_TEMPLATE = "# {index}. {title}\n{snippet}"
CITATION_TEMPLATE = "[{index}] [{title}]({link})"


def process_results(results: List[SearchResult]) -> Iterator[Tuple[str, str]]:
    """生成显示内容和引用链接的元组迭代器

    Parameters
    ----------
    results: List[SearchResult]
        搜索结果列表

    Yields
    ----------
    Tuple[str, str]
        (显示内容, 引用链接)
    """
    for index, (title, snippet, link) in enumerate(results, start=1):
        yield (
            RESULT_TEMPLATE.format(index=index, title=title, snippet=snippet),
            CITATION_TEMPLATE.format(index=index, title=title, link=link),
        )


async def generate_search_results(
    query: str, search_func: SearchFunction
) -> Tuple[str, str]:
    """通用搜索结果生成函数

    Parameters
    ----------
    query: str
        搜索关键词
    search_func: SearchFunction
        搜索函数。可能为searxng_websearch或select_academic_search_result

    Returns
    ----------
    Tuple[str, str]
        (显示内容, 引用链接)
    """
    search_results = await search_func(query)
    if search_results:
        display_lines, citation_lines = (
            zip(*process_results(search_results)) if search_results else ([], [])
        )
        return "\n\n".join(display_lines), "\n\n".join(citation_lines)
    return (
        "未能找到相关结果，模型请结合自身知识与理解回答",
        "# 系统提示：未能找到相关结果",
    )


async def attach_web_result(query: str) -> Tuple[str, str]:
    """附加网页搜索结果

    Parameters
    ----------
    query: str
        搜索关键词

    Returns
    ----------
    Tuple[str, str]
        (显示内容, 引用链接)
    """
    return await generate_search_results(query, searxng_websearch)


async def attach_academic_result(query: str) -> Tuple[str, str]:
    """附加论文搜索结果

    Parameters
    ----------
    query: str
        搜索关键词

    Returns
    ----------
    Tuple[str, str]
        (显示内容, 引用链接)
    """
    return await generate_search_results(query, select_academic_search_result)


async def generate_academic_search_summary(
    query: str,
) -> AsyncGenerator[str, None]:
    """生成论文搜索概述

    Parameters
    ----------
    query: str
        搜索关键词

    Yields
    ----------
    str
        概述。Gradio不支持增量更新，每次返回完整字符串
    """
    best_results, reference = await attach_academic_result(query)
    prompt = await generate_summary_prompt_tempate.ainvoke(
        {"content": f"\n搜索引擎前10结果：\n{best_results}\n{query}"}
    )
    final_response = StringIO()
    yield final_response.getvalue()
    response = deepseek_v3.astream(prompt)
    async for chunk in response:
        final_response.write(chunk.content)
        yield final_response.getvalue()
    final_response.write(f"\n\n参考文献\n\n{reference}")
    yield final_response.getvalue()
    final_response.close()
