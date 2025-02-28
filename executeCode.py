import subprocess
import re

EXTRACT_MAIN_PATTERN = re.compile(r'In \[1\]:\s*(.*?)\nIn', re.DOTALL)
CLEAN_LINE_PATTERN = re.compile(r'^In \[\d+\]:|^Out\[\d+\]:\s*')

def execute_code(code: str) -> str:
    process = subprocess.Popen(
        ['ipython'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout_output, stderr_output = process.communicate(code)
    
    output_blocks = []
    
    if stdout_output:
        match = EXTRACT_MAIN_PATTERN.search(stdout_output)
        if match:
            extracted_output = match.group(1)
            cleaned_lines = [
                CLEAN_LINE_PATTERN.sub('', line.strip()).strip()
                for line in extracted_output.split('\n')
            ]
            cleaned_lines = [line for line in cleaned_lines if line]
            cleaned_output = '\n'.join(cleaned_lines)
            
            code_block = f'```python\n{code}\n```'
            output_blocks.append(code_block)
            
            if cleaned_output:
                output_blocks.append(f'```output\n{cleaned_output}\n```')
    
    error_block = ''
    if stderr_output:
        error_block = f'```error\n{stderr_output}\n```'
    
    return '\n'.join(output_blocks + [error_block]) if error_block else '\n'.join(output_blocks)


def insert_python(code: str) -> str:
    return f'\n\n{execute_code(code)}\n'
