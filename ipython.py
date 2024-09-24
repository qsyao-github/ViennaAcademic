import subprocess
import tempfile
import os


def execute_code(code):
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.py',
                                     delete=False) as tf:
        temp_file_name = tf.name
        tf.write(code)
    try:
        result = subprocess.check_output(['python', temp_file_name],
                                         stderr=subprocess.STDOUT)
        return (result.decode('utf-8'))
    except subprocess.CalledProcessError as e:
        return e.output.decode('utf-8')
    finally:
        os.remove(temp_file_name)
