from .academic_search_tool import academic_search
from .mcp_tools import get_mcp_tools
from .tavily_tool import general_search
from typing import Literal

ToolName = Literal["ipython", "general_search", "academic_search"]


async def get_tools():
    tools = await get_mcp_tools()
    tools.extend((academic_search, general_search))
    return tools


def format_tool_call(tool_call: dict[str, str]):
    if tool_call["name"] == "ipython":
        return f'```python\n{tool_call["args"]["code"]}\n```'
    if tool_call["name"] == "general_search":
        return f'```\n联网搜索:\n{tool_call["args"]["query"]}\n```'
    if tool_call["name"] == "academic_search":
        return f'```\n学术搜索:\n{tool_call["args"]["query"]}\n```'
