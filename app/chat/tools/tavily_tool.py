from langchain.tools import tool
from tavily import AsyncTavilyClient
import os

client = AsyncTavilyClient(os.getenv("TAVILY_API_KEY"))


@tool
async def general_search(query: str) -> str:
    """用Tavily搜索，中英文搜索结果可能质量不同，不适合复杂学术问题/论文搜索"""
    search_response = await client.search(
        query,
        auto_parameters=True,
        search_depth="basic",
        include_answer="advanced",
    )
    answer = search_response["answer"]
    results = search_response["results"]
    # 格式化输出
    formated_results = "\n\n---\n\n".join(
        f'[{result["title"]}]({result["url"]})\n\n```\n{result["content"]}\n```'
        for result in results
    )
    formated_answer = f"{answer}\n\n---\n\n{formated_results}"
    return formated_answer
