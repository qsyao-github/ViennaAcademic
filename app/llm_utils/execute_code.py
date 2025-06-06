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


def get_base_path(tar_info: TarInfo) -> TarInfo:
    """
    去除tar_info中的路径前缀，使其只包含文件名

    Parameters
    ----------
    tar_info: TarInfo
        原始tar_info

    Returns
    ----------
    TarInfo
        去除路径前缀的tar_info
    """
    tar_info.path = os.path.basename(tar_info.path)
    return tar_info


def copy_file(stream) -> None:
    """
    将png文件夹tar流解压并写入本地

    Parameters
    ----------
    stream: Incomplete
        tar流
    """
    tar_data = BytesIO()
    for chunk in stream:
        tar_data.write(chunk)
    tar_data.seek(0)
    with tarfile.open(fileobj=tar_data) as tar:
        tar.extractall(
            "media",
            members=tar,
            numeric_owner=True,
        )


def python_tool(code: str, thread_id) -> str:
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
    # 单独为线程分配工作目录
    workdir = f"/root/{thread_id}"
    # 将报错信息改为了无色，防止彩色转义符在Gradio端渲染异常/影响模型输出。用timeout命令限制执行时间
    exec_id = container.exec_run(f"mkdir -p {thread_id}")
    exec_id = container.exec_run(
        f'timeout -k {KILL_AFTER} {TIMEOUT} ipython --InteractiveShell.ast_node_interactivity=all --colors=NoColor -c "{code.replace('"', "'")}"',
        workdir=workdir,
    )
    # 获取执行结果，处理超时
    if exec_id.exit_code == 124:
        return f"执行超时：用时超过{TIMEOUT}s，请勿重试"
    output = f'\n```\n{clean_output_pattern.sub("", exec_id.output.decode("utf-8").strip())}\n```\n\n'
    # png文件处理
    container_png_files_str = container.exec_run(
        "ls -1 | grep png", workdir=workdir
    ).output.decode("utf-8")
    if not container_png_files_str:
        return output
    # 获取整个文件夹的tar流
    stream, _ = container.get_archive(workdir)
    copy_file(stream)
    # 删除线程目录
    container.exec_run(f"rm -rf {thread_id}")
    return output
