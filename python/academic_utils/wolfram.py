"""
WolframAlpha结果处理
"""

from python.web_utils.crawler import get_wolfram


async def attach_hints(query: str) -> str:
    """在询问前附加WolframAlpha的提示信息

    Parameters
    ----------
    query: str
        搜索词

    Returns
    ----------
    query: str
        附加提示后的搜索词
    """
    if hints := await get_wolfram(query):
        query = f"Wolframalpha提示：\n```\n{hints}\n```\n{query}"
    return query
