import subprocess
from generate import extract_content, isChinese
from collections import deque


def convert_to_pdf(input_file):
    subprocess.run([
        'pandoc', input_file, '--pdf-engine=xelatex','-V',
        'CJKmainfont=AR PL SungtiL GB', '-o',
        input_file.split('.')[-2] + '.pdf'
    ])


def convert_to(input_file, extension):
    if extension == 'pdf':
        convert_to_pdf(input_file)
    else:
        subprocess.run([
            'pandoc', input_file, '-o',
            input_file.split('.')[-2] + '.' + extension
        ])


def extract_from_toc(toc):
    subheadings = deque()
    for line in toc.splitlines():
        level = (len(line) - len(line.lstrip(' '))) // 4
        if level > 1:
            subheadings.append('#' * level + ' ' + line.strip(' -'))
    return subheadings


def parse_markdown(input_file):
    with open(input_file + '.md', 'r') as f:
        content = f.read()
    first_sharp = content.find('# ')
    if first_sharp == -1:
        return ''
    last_sharp = content.rfind('## 参考文献')
    if last_sharp == -1:
        last_sharp = content.rfind('## Reference')
    toc, content, reference = content[:first_sharp].strip(
    ), content[first_sharp:last_sharp].strip(), content[last_sharp:].strip()
    # subheadings = extract_from_toc(toc) if toc else deque()
    newContents = extract_content(content, isChinese(toc))
    referenceSplit = reference.split('\n', 1)
    newReference = f"{referenceSplit[0]} {{.allowframebreaks}}{referenceSplit[1]}"
    for newContent in newContents:
        yield f"{newContent}\n\n{newReference}"


def convert_to_pptx(input_file, do_parse=True):
    if do_parse:
        finalcontent = ''
        contents = parse_markdown(input_file)
        for content in contents:
            finalcontent = content
            yield content
        with open(input_file + 'ppt.md', 'w', encoding='utf-8') as f:
            f.write(finalcontent)
    else:
        with open(input_file + 'ppt.md', 'r', encoding='utf-8') as f:
            finalcontent = f.read()
        yield finalcontent
    subprocess.run([
        'pandoc', input_file + 'ppt.md', '-t', 'beamer',
        '--pdf-engine=xelatex', '-V', 'theme:Madrid', '-V',
        'CJKmainfont=AR PL SungtiL GB', '--slide-level', '2', '-o',
        input_file + 'ppt.pdf'
    ])
