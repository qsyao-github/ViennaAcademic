import subprocess
import re

EXTRACT_MAIN_PATTERN = re.compile(r'In \[1\]:\s*(.*?)\nIn', re.DOTALL)
CLEAN_LINE_PATTERN = re.compile(r'^In \[\d+\]:|^Out\[\d+\]:')


def execute_code(code):
    process = subprocess.Popen(['ipython'],
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               text=True)
    stdout, stderr = process.communicate(code)
    if stdout:
        stdout = f'```python\n{code}\n```\n```output\n{EXTRACT_MAIN_PATTERN.search(stdout).group(1)}\n```'
        lines = stdout.split('\n')
        outputList = []
        for line in lines:
            cleanedLine = CLEAN_LINE_PATTERN.sub('', line.strip()).strip()
            if cleanedLine:
                outputList.append(cleanedLine)
        stdout = '\n'.join(outputList)
    return (stdout if stdout else '') + (f'```error\n{stderr}\n```'
                                         if stderr else '')

def insert_python(code):
    return f'\n\n{execute_code(code)}\n'
