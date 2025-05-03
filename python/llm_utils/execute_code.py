"""
使用scipy-light容器执行命令，该容器由scipy-light/Dockerfile构建

启动容器(先于demo.py)：
docker run -d --rm --name scipy-light scipy-light
"""

import subprocess
import re

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
    1. 使用get_archive处理png文件，复制到容器外后迅速删除
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
    container_png_files = set(container_png_files_str.strip().split("\n"))
    # 复制文件
    subprocess.run(
        [
            "sh",
            "-c",
            " && ".join(
                [
                    f"docker cp scipy-light:/home/jovyan/{png_file} media/{png_file}"
                    for png_file in container_png_files
                ]
            ),
        ]
    )
    container.exec_run(f"rm {' '.join(container_png_files)}")
    return output
