"""
工具调用排版
"""

import re

"""匹配工具调用内容"""
TOOL_CALL_PATTERN = re.compile(r'\{\s*("[^"]+"):\s*("(?:\\"|[^"])*")\s*\}', re.DOTALL)
"""根据调用类型格式化调用信息"""
TOOLS = {
    '"query"': lambda x: f"\n```\n{x.strip('"').replace(r'\n', '\n')}\n```\n",
    '"code"': lambda x: f"\n```python\n{x.strip('"').replace(r'\n', '\n')}\n```\n",
}


def format_tools(text: str) -> str:
    """工具调用排版

    Parameters
    ----------
    text: str
        待处理文本

    Returns
    ----------
    str
        处理后文本
    """

    def replace_tag(match: re.Match) -> str:
        """替换工具调用内容

        匹配工具名称及参数，并调用TOOLS中对应的函数，将整体替换为结果

        Parameters
        ----------
        match: re.Match
            匹配结果

        Returns
        ----------
        str
            替换后的文本
        """
        arg_name, arg_value = match.groups()
        formatter = TOOLS.get(arg_name)
        if not arg_value or not formatter:
            return match.group(0)
        return formatter(arg_value)

    return TOOL_CALL_PATTERN.sub(replace_tag, text)
