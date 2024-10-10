import subprocess
import tempfile
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
    return stdout if stdout else '' + stderr if stderr else ''


def manim_render(code):
    # 找到code中construct方法
    start = code.find('def construct(self):')
    # 在construct后的换行符后添加：\usepackage{CJK}
    code = "from manim import *\n"
    # 删除相对路径media/videos/中所有文件夹名不为fileNames的文件夹
    os.chdir(r'C:\Users\15081\Desktop\glmacademic')
    # 强制删除media文件夹(非空)
    shutil.rmtree('media')
    # 保存临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=True) as f:
        f.write(code)
        f.flush()
        os.fsync(f.fileno())
        # 用manim指令
        process = subprocess.Popen(['manim', f.name, '-ql'])
        process.wait()
        fileName = f.name.strip('.py')

    # 找到最近的输出文件的目录
    output_dir = max([
        os.path.join(os.path.dirname(f.name),
                     f'media/videos/{fileName}/480p15')
        for f in os.scandir(os.path.dirname(f.name)) if f.is_dir()
    ],
                     key=os.path.getmtime)
    return output_dir
