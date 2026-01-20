from langchain.tools import tool
from semanticscholar import AsyncSemanticScholar

sch = AsyncSemanticScholar()


def info_to_text(paper_data):
    """将Semantic Scholar结构化数据转换为markdown片段"""
    if paper_data["tldr"] is not None and paper_data["tldr"]["text"] is not None:
        return f'[{paper_data["title"]}]({paper_data["url"]})\n\n{paper_data["tldr"]["text"]}'
    return f'[{paper_data["title"]}]({paper_data["url"]})\n\n{paper_data["abstract"]}'


@tool
async def academic_search(query: str) -> str:
    """用用户知识库/Semantic Scholar搜索有关论文片段/摘要，中英文搜索结果可能质量不同"""
    results = await sch.search_paper(
        query,
        fields=[
            "url",
            "title",
            "abstract",
            "citationCount",
            "influentialCitationCount",
            "textAvailability",
            "tldr",
        ],
        limit=100,
    )
    # 过滤出有tldr或abstract的
    response = [
        item
        for item in results.items
        if (item["tldr"] is not None and item["tldr"]["text"] is not None)
        or item["abstract"]
    ]
    # 按引用/影响力引用过滤，保留20篇
    have_citation = [item for item in response if item["citationCount"] > 0]
    have_influential_citation = [
        item for item in response if item["influentialCitationCount"] > 0
    ]
    if len(have_influential_citation) >= 20:
        response = have_influential_citation
    elif len(have_citation) >= 20:
        response = have_citation
    response = [info_to_text(item) for item in response]
    return "\n\n---\n\n".join(response[:20])
