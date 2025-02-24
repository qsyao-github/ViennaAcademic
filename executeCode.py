import subprocess
import os
import shutil
import re


def execute_code(code):
    process = subprocess.Popen(['ipython'],
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               text=True)
    stdout, stderr = process.communicate(code)
    if stdout:
        stdout = '```python\n' + code + '\n```\n```output\n' + stdout[
            stdout.find('In [1]: ') + 8:stdout.rfind('\nIn')] + '\n```'
        lines = stdout.split('\n')
        outputList = []
        for line in lines:
            cleanedLine = re.sub(r'^In \[\d+\]:|^Out\[\d+\]:', '', line.strip()).strip()
            if cleanedLine:
                outputList.append(cleanedLine)
        stdout = '\n'.join(outputList)
    return stdout if stdout else '' + f'```error\n{stderr}\n```' if stderr else ''


outputFolder = r'media/videos/temp/480p15/'
def manim_render(code, nowTime):
    try:
        if '```' in code:
            code = code[code.find('```python') + 10:code.rfind('```')]
        if os.path.exists('media'):
            shutil.rmtree('media')
        with open('temp.py', 'w') as f:
            f.write("from manim import *\n" + code)
        subprocess.run(['manim', 'temp.py', '-ql'], check=True)
        output = [f for f in os.listdir(outputFolder) if f.endswith('.mp4')][0]
        new_output_path = os.path.join(outputFolder, f'{nowTime}.mp4')
        os.rename(os.path.join(outputFolder, output), new_output_path)
        shutil.move(new_output_path, os.getcwd())
        return f'```python\n{code}\n```'
    except:
        return 'gpt生成代码有误，请重试'
