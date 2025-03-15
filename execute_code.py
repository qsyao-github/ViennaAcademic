"""
使用gVisor保护的scipy-notebook容器执行命令

启动容器(先于demo.py)：
docker run --runtime=runsc --rm -v /home/{user_name}/{working_dir}/media:/home/jovyan -d -p 8888:8888 --name scipy-notebook quay.io/jupyter/scipy-notebook
"""

import re

import docker

"""清除输出中的Out[...]"""
clean_output_pattern = re.compile(r"Out\[\d+\]:\s*")
client = docker.from_env()
container = client.containers.get("scipy-notebook")


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
    """
    # 将报错信息改为了无色，防止彩色转义符在Gradio端渲染异常/影响模型输出
    exec_id = container.exec_run(
        f'ipython --InteractiveShell.ast_node_interactivity=all --colors=NoColor -c "{code.replace("\"", "\'")}"'
    )
    # 获取执行结果
    output = exec_id.output.decode("utf-8")
    return f'```\n{clean_output_pattern.sub("", output).strip()}\n```\n\n'
