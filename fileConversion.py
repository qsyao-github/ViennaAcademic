import subprocess
from generate import extract_content, isChinese
import os


def convert_to_pdf(input_file):
    file_name, _ = os.path.splitext(input_file)
    result_file = f'{file_name}.typ'
    result = subprocess.run(['pandoc', '-f', 'markdown', '-t', 'typst', input_file], capture_output=True, text=True).stdout
    result = """#set text(font: (
  (name: "libertinus serif", covers: "latin-in-cjk"),
  "Noto Sans CJK SC"
))\n""" + result
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write(result)
    subprocess.run(['./typst', 'compile', result_file])
    os.remove(result_file)



def convert_to(input_file, extension):
    if extension == 'pdf':
        convert_to_pdf(input_file)
    else:
        file_name, _ = os.path.splitext(input_file)
        subprocess.run(
            ['pandoc', input_file, '-o', f'{file_name}.{extension}'])


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
    newContents = extract_content(content, isChinese(toc))
    referenceSplit = reference.split('\n', 1)
    newReference = f"{referenceSplit[0]} {{.allowframebreaks}}{referenceSplit[1]}"
    for newContent in newContents:
        yield f"{newContent}\n\n{newReference}"


def convert_to_pptx(input_file, do_parse=True):
    output_md_file = f'{input_file}ppt.md'
    if do_parse:
        finalcontent = ''
        contents = parse_markdown(input_file)
        for content in contents:
            finalcontent = content
            yield content
        with open(output_md_file, 'w', encoding='utf-8') as f:
            f.write(finalcontent)
    else:
        with open(output_md_file, 'r', encoding='utf-8') as f:
            finalcontent = f.read()
        yield finalcontent
    subprocess.run([
        'pandoc', output_md_file, '-t', 'beamer', '--pdf-engine=xelatex', '-V',
        'theme:Madrid', '-V', 'CJKmainfont=AR PL SungtiL GB', '--slide-level',
        '2', '-o', f'{input_file}ppt.pdf'
    ])


"""pandoc -f markdown -t typst path1 -o path2"""
"""./typst compile path"""
"""#set text(font: (
  (name: "libertinus serif", covers: "latin-in-cjk"),
  "Noto Sans CJK SC"
))"""
