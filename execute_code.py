import subprocess
import re
from langchain_core.tools import tool

CLEAN_LINE_PATTERN = re.compile(r"^In \[\d+\]:\s*Out\[\d+\]:\s*")


def execute_code(code: str) -> str:
    process = subprocess.Popen(
        ["ipython"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout_output, _ = process.communicate(code)

    output_blocks = []

    if (index := stdout_output.find("In [1]")) != -1:
        stdout_output = stdout_output[index:stdout_output.rfind("In [")]
        splitted_output = stdout_output.split("\n")
        for i, line in enumerate(splitted_output):
            if not line[line.rfind(':')+1:].strip():
                splitted_output[i] = ''
            elif 'Out' in line:
                splitted_output[i] = line[line.find(':')+2:]
        cleaned_output = '\n'.join([line for line in splitted_output if line])

        code_block = f"```python\n{code}\n```"
        output_blocks.append(code_block)

        if cleaned_output:
            output_blocks.append(f"```\n{cleaned_output}\n```")

    return f"\n\n{'\n'.join(output_blocks)}\n"

@tool
def python(code: str) -> str:
    """Ipython cell. Use numpy, scipy, sympy for numeric and symbolic computation."""
    process = subprocess.Popen(
        ["ipython"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout_output, _ = process.communicate(code)
    if (index := stdout_output.find("In [1]")) != -1:
        stdout_output = stdout_output[index:stdout_output.rfind("In [")]
        splitted_output = stdout_output.split("\n")
        for i, line in enumerate(splitted_output):
            if not line[line.rfind(':')+1:].strip():
                splitted_output[i] = ''
            elif 'Out' in line:
                splitted_output[i] = line[line.find(':')+2:]
    return '\n'.join([line for line in splitted_output if line])
