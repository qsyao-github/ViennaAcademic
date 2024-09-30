import subprocess


def execute_code(code):
    process = subprocess.Popen(['ipython'],
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               text=True)
    stdout, stderr = process.communicate(code)
    if stdout:
        stdout = 'In[1]: ' + code + '\n' + stdout[stdout.find('In [1]: ') +
                                                  8:stdout.rfind('\n\nIn [2]: '
                                                                 )]
    return stdout if stdout else '' + stderr if stderr else ''
