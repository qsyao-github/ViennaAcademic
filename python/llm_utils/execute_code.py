"""
使用gVisor保护的scipy-notebook容器执行命令

启动容器(先于demo.py)：
docker run --runtime=runsc --rm -d -p 127.0.0.1:8888:8888 --name scipy-notebook quay.io/jupyter/scipy-notebook
"""

import os
import re
from typing import List

import docker

# 优雅退出时限
TIMEOUT = 30
# 强制退出时限
KILL_AFTER = 1
# 清除输出中的Out[...]
clean_output_pattern = re.compile(r"Out\[\d+\]:\s*")
# 连接容器
client = docker.from_env()
container = client.containers.get("scipy-notebook")


def get_png_files() -> List[str]:
    """获取容器中的png文件

    Returns
    ----------
    List[str]
        png文件名列表
    """
    files = (
        container.exec_run("sh -c 'ls -1 | grep png'").output.decode("utf-8").strip()
    )
    return files.split("\n")


def delete_png_files() -> None:
    """删除容器中的png文件"""
    container.exec_run("sh -c 'rm -f *.png'")


def python_tool(code: str) -> str:
    """通过容器执行Python代码

    Parameters
    ----------
    code: str
        待执行的Python代码

    Returns
    ----------
    str
        执行结果。清洗后放入文本框中

    Notes
    ----------
    1. 对matplotlib生成图片，使用cat获取二进制流写入本地(gVisor限制docker cp)
    """
    # 将报错信息改为了无色，防止彩色转义符在Gradio端渲染异常/影响模型输出。用timeout命令限制执行时间
    exec_id = container.exec_run(
        f'timeout -k {KILL_AFTER} {TIMEOUT} ipython --InteractiveShell.ast_node_interactivity=all --colors=NoColor -c "{code.replace("\"", "\'")}"'
    )
    # 获取执行结果，处理超时
    timeout = exec_id.exit_code == 124
    output = (
        f"执行超时：用时超过{TIMEOUT}s，请勿重试"
        if timeout
        else exec_id.output.decode("utf-8")
    )
    # png文件处理
    png_files = get_png_files()
    for png_file in png_files:
        if not os.path.exists(f"media/{png_file}"):
            with open(f"media/{png_file}", "wb") as f:
                f.write(container.exec_run(f"cat /home/jovyan/{png_file}").output)
    return f'```\n{clean_output_pattern.sub("", output).strip()}\n```\n\n'
