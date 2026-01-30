"""
所有mcp工具

- ipython代码执行
"""

import os

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

scipy_light_port = os.getenv("SCIPY_LIGHT_PORT", "8000")
client = MultiServerMCPClient(
    {
        "ipython": {
            "transport": "http",
            "url": f"http://scipy-light:{scipy_light_port}/mcp",
        }
    }
)


async def get_mcp_tools() -> list[BaseTool]:
    tools = await client.get_tools()
    return tools
