import subprocess
import os
import shutil
import time


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
    return stdout if stdout else '' + stderr if stderr else ''


def manim_render(code):

    start = code.find('def construct(self):')

    code = "from manim import *\n" + code

    os.chdir(r'C:\Users\15081\Desktop\glmacademic')

    if os.path.exists('media'):
        shutil.rmtree('media')

    with open('temp.py', 'w') as f:
        f.write(code)
    os.system(f'manim temp.py -ql')
    os.chdir(r'C:/Users/15081/Desktop/glmacademic/media/videos/temp/480p15')
    output_dir = [f for f in os.listdir() if f.endswith('.mp4')][0]
    return output_dir
