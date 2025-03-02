import os
file_suffix_to_markdown = {
    'py': 'python',
    'c': 'c',
    'cpp': 'cpp',
    'md': 'markdown',
    'json': 'json',
    'html': 'html',
    'css': 'css',
    'js': 'javascript',
    'jinja2': 'jinja2',
    'ts': 'typescript',
    'yaml': 'yaml',
    'dockerfile': 'dockerfile',
    'sh': 'shell',
    'r': 'r',
    'sql': 'sql',
}
def attach(file, current_user_directory):
    file_name, file_suffix = os.path.splitext(file)
    knowledgeBase_path = os.path.join(current_user_directory, 'knowledgeBase', f'{file_name}.md')
    if os.path.exists(knowledgeBase_path):
        with open(knowledgeBase_path, 'r', encoding='utf-8') as f:
            return f.read()
    code_path = os.path.join(current_user_directory, 'code', file)
    if os.exists(code_path):
        with open(code_path, 'r', encoding='utf-8') as f:
            code = f.read()
        return f'```{file_suffix_to_markdown.get(file_suffix, '')}\n{code}\n```'
