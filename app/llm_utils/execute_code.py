"""
使用scipy-light容器执行命令，该容器由scipy-light/Dockerfile构建

启动容器(先于demo.py)：
docker run -d --rm --name scipy-light scipy-light
"""

import os
import re
import tarfile
from io import BytesIO
from tarfile import TarInfo

import docker

# 优雅退出时限
TIMEOUT = 30
# 强制退出时限
KILL_AFTER = 1
# 清除输出中的Out[...]
clean_output_pattern = re.compile(r"Out\[\d+\]:\s*")
# 连接容器
client = docker.from_env()
container = client.containers.get("scipy-light")


def get_base_path(tar_info: TarInfo):
    tar_info.path = os.path.basename(tar_info.path)
    return tar_info


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
    1. 使用get_archive打包png文件为tar，复制到容器外后解压，删除容器内的png
    """
    # 将报错信息改为了无色，防止彩色转义符在Gradio端渲染异常/影响模型输出。用timeout命令限制执行时间
    exec_id = container.exec_run(
        f'timeout -k {KILL_AFTER} {TIMEOUT} ipython --InteractiveShell.ast_node_interactivity=all --colors=NoColor -c "{code.replace("\"", "\'")}"'
    )
    # 获取执行结果，处理超时
    if exec_id.exit_code == 124:
        return f"执行超时：用时超过{TIMEOUT}s，请勿重试"
    output = f'\n```\n{clean_output_pattern.sub("", exec_id.output.decode("utf-8").strip())}\n```\n\n'
    # png文件处理
    container_png_files_str = container.exec_run(
        "sh -c 'ls -1 | grep png'"
    ).output.decode("utf-8")
    if not container_png_files_str:
        return output
    # 创建临时文件夹并移动文件
    container.exec_run("mkdir -p /tmp/png_output")  # 创建专用目录
    container.exec_run(
        "sh -c 'mv /root/*.png /tmp/png_output/'",
        workdir="/root",
    )
    # 获取整个文件夹的tar流
    stream, _ = container.get_archive("/tmp/png_output")
    # 解压到本地
    tar_data = BytesIO()
    for chunk in stream:
        tar_data.write(chunk)
    tar_data.seek(0)
    with tarfile.open(fileobj=tar_data) as tar:
        tar.extractall(
            "media",
            members=[get_base_path(m) for m in tar if m.isfile()],
            numeric_owner=True,
        )
    container.exec_run("rm -rf /tmp/png_output")
    return output
