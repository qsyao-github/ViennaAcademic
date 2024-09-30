import ollama
import os


def codegeex_generate(prompt):
    answer = ""
    stream = ollama.chat(
        model='codegeex4',
        messages=[{
            'role': 'user',
            'content': prompt
        }],
        stream=True,
    )
    for chunk in stream:
        chunks = chunk['message']['content']
        answer += chunks
    return answer


def is_program_file(filename):
    program_extensions = {
        '.vue', '.js', '.ts', '.html', '.htm', '.css', '.jsx', '.c', '.cpp',
        '.cxx', '.cc', '.java', '.py', '.go', '.php', '.rs', '.sql', '.m',
        '.mm', '.kt', '.swift', '.pl', '.pm', '.rb', '.graphql', '.gql',
        '.cbl', '.cob', '.h', '.hpp'
    }
    _, ext = os.path.splitext(filename)
    return ext.lower() in program_extensions


def get_folder_structure(folder_path):
    structure = {
        'path': folder_path[folder_path.rfind('\\') + 1:],
        'subfolders': [],
        'files': []
    }
    with os.scandir(folder_path) as entries:
        for entry in entries:
            if entry.is_dir(follow_symlinks=False):
                structure['subfolders'].append(get_folder_structure(
                    entry.path))
            elif entry.is_file():
                if is_program_file(entry.name):
                    with open(entry.path, 'r', encoding='utf-8') as file:
                        code = file.read()
                    prompt = f"请用一句话概括{entry.name}的功能，代码: \n{code}\n，只需概括，不需解释函数、类的作用，一句话即可。请用中文回答"
                    file_function = codegeex_generate(prompt)
                    structure['files'].append((entry.name, file_function))
        return structure


def generate_mermaid(structure):
    mermaid_str = "graph LR\n"
    for folder in structure['subfolders']:
        mermaid_str += f"{structure['path']}---{folder['path']}\n"
        mermaid_str += generate_mermaid(folder)
    for file in structure['files']:
        mermaid_str += f"{structure['path']}---{file[0]}\n"
    return mermaid_str


def find_files_comment(structure):
    commentPair = []
    for folder in structure['subfolders']:
        commentPair += find_files_comment(folder)
    return commentPair + [(file[0], file[1]) for file in structure['files']]


def generate_markdown(commentPair):
    markdown_str = "|文件名|功能概括|\n|:-:|:-:|\n"
    for file, comment in commentPair:
        markdown_str += f"|{file}|{comment}|\n"
    return markdown_str


def analyze_folder(folder_path):
    structure = get_folder_structure(folder_path)
    repoStructure = generate_mermaid(structure)
    repoFunction = generate_markdown(find_files_comment(structure))
    return repoStructure + '\n' + repoFunction
