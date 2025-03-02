import subprocess
import re

CLEAN_LINE_PATTERN = re.compile(r'^In \[\d+\]:\s*Out\[\d+\]:\s*')


def execute_code(code: str) -> str:
    process = subprocess.Popen(['ipython'],
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               text=True)
    stdout_output, stderr_output = process.communicate(code)

    output_blocks = []

    if stdout_output:
        extracted_output_list = [
            line for line in stdout_output.split('\n') if 'Out' in line
        ]
        cleaned_lines = [
            CLEAN_LINE_PATTERN.sub('', line.strip()).strip()
            for line in extracted_output_list
        ]
        cleaned_lines = [line for line in cleaned_lines if line]
        cleaned_output = '\n'.join(cleaned_lines)

        code_block = f'```python\n{code}\n```'
        output_blocks.append(code_block)

        if cleaned_output:
            output_blocks.append(f'```\n{cleaned_output}\n```')

    error_block = ''
    if stderr_output:
        error_block = f'```error\n{stderr_output}\n```'

    return f"\n\n{'\n'.join(output_blocks + [error_block]) if error_block else '\n'.join(output_blocks)}\n"
