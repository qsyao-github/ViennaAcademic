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
    return stdout if stdout else '' + stderr if stderr else ''


def manim_render(code, nowTime):
    try:
        if '```' in code:
            code = code[code.find('```python') + 10:code.rfind('```')]
        if os.path.exists('media'):
            shutil.rmtree('media')
        with open('temp.py', 'w') as f:
            f.write("from manim import *\n" + code)
        os.system(f'manim temp.py -ql')
        outputFolder = r'media/videos/temp/480p15/'
        output = [f for f in os.listdir(outputFolder) if f.endswith('.mp4')][0]
        os.rename(outputFolder + output, outputFolder + nowTime + '.mp4')
        shutil.move(outputFolder + nowTime + '.mp4', os.getcwd())
        return f'```python\n{code}\n```'
    except:
        return 'gpt生成代码有误，请重试'
