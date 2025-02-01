import subprocess
import os
import shutil


def execute_code(code):
    process = subprocess.Popen(['ipython'],
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               text=True)
    stdout, stderr = process.communicate(code)
    if stdout:
        stdout = 'In[1]: ' + code + '\n' + stdout[stdout.find('In [1]: ') +
                                                  8:stdout.rfind('\nIn')]
        outputList = stdout.split('\n')
        outputList = [
            line for line in stdout.split('\n')
            if line.strip().split(':')[-1].strip() != ''
        ]
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
        output = [
            f for f in os.listdir(outputFolder)
            if f.endswith('.mp4')
        ][0]
        os.rename(outputFolder + output, outputFolder + nowTime + '.mp4')
        shutil.move(outputFolder + nowTime + '.mp4', os.getcwd())
        return nowTime + '.mp4'
    except:
        return 'gpt生成代码有误，请重试'
