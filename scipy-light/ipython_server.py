"""
执行ipython代码的mcp服务

启动：fastmcp run ipython_server.py:mcp --transport http --host "0.0.0.0" --port 8000
"""

import asyncio
import io
import os
from concurrent.futures import ProcessPoolExecutor

from fastmcp import FastMCP
from fastmcp.utilities.types import Image
from IPython.core.interactiveshell import InteractiveShell
from IPython.utils.capture import capture_output

# 消除颜色
os.environ["TERM"] = "dumb"
os.environ["FORCE_COLOR"] = "0"
os.environ["NO_COLOR"] = "1"

mcp = FastMCP("Scipy Light")

# 用于提取matplotlib图片的代码，在ipython shell中执行
GET_FIGURES_BASE64 = """from matplotlib._pylab_helpers import Gcf
Gcf.get_all_fig_managers()"""


def execute_shell(code: str) -> tuple[str, list[bytes]]:
    """执行代码

    Args:
        code (str)

    Returns:
        tuple[str, list[bytes]]: 第一项为代码产生的stdout，第二项为所有图片的二进制

    Notes:
        需要单开一个线程运行
    """
    # 消除颜色
    shell = InteractiveShell(colors="nocolor")
    # 获取该进程的标准输出
    with capture_output() as captured:
        shell.run_cell(code)
    # 提取所有该shell的matplotlib图表
    figures = []
    for manager in shell.run_cell(GET_FIGURES_BASE64).result:
        buf = io.BytesIO()
        manager.canvas.figure.savefig(buf, format="png", bbox_inches="tight")
        figures.append(buf.getvalue())
    return (captured.stdout, figures)


@mcp.tool
async def ipython(code: str) -> list[str | Image]:
    """用独立的ipython代码单元执行ipython代码和魔术命令。可用numpy, scipy, pandas, sympy, matplotlib, seaborn, scikit-learn, statsmodels, patsy, bottleneck"""
    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor(max_workers=1) as executor:
        output, figures = await loop.run_in_executor(executor, execute_shell, code)
    tool_messages: list[str | Image] = [output]
    tool_messages.extend(Image(data=figure) for figure in figures)
    return tool_messages
