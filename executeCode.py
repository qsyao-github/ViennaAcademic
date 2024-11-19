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
            line for line in outputList
            if line[line.rfind(':') + 1:line.rfind('\n')] != ''
        ]
        stdout = '\n'.join(outputList)
    return stdout if stdout else '' + stderr if stderr else ''


def manim_render(code, nowTime):
    code = "from manim import *\n" + code
    if os.path.exists('media'):
        shutil.rmtree('media')
    with open('temp.py', 'w') as f:
        f.write(code)
    os.system(f'manim temp.py -ql')
    output = [
        f for f in os.listdir(r'media/videos/temp/480p15/')
        if f.endswith('.mp4')
    ][0]
    os.rename(r'media/videos/temp/480p15/' + output,
              r'media/videos/temp/480p15/' + nowTime + '.mp4')
    shutil.move(r'media/videos/temp/480p15/' + nowTime + '.mp4', os.getcwd())
    return nowTime + '.mp4'
