import subprocess
from generate import extract_content, isChinese
import os
import re

def convert_to_typst(input_file):
    file_name, _ = os.path.splitext(input_file)
    result_file = f'{file_name}.typ'
    result = subprocess.run(
        ['pandoc', '-f', 'markdown', '-t', 'typst', input_file],
        capture_output=True,
        text=True).stdout
    result = f"""#set text(font: (
  (name: "libertinus serif", covers: "latin-in-cjk"),
  "Noto Sans CJK SC"
))
{result}"""
    result = re.sub(r'<.*?>', '', result)
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write(result)
def convert_to_pdf(input_file):
    file_name, _ = os.path.splitext(input_file)
    result_file = f'{file_name}.typ'
    convert_to_typst(input_file)
    subprocess.run(['./typst', 'compile', result_file])
    os.remove(result_file)

def convert_to(input_file, extension):
    if extension == 'pdf':
        convert_to_pdf(input_file)
    elif extension == 'typ':
        convert_to_typst(input_file)
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
    newReference = f"{referenceSplit[0]}\n{referenceSplit[1]}"
    for newContent, title in newContents:
        yield f"{newContent}\n\n{newReference}", title


def get_template(theme, final_title, result):
    if theme == 'stargazer':
            result = f"""#import "@preview/touying:0.6.0": *
#import themes.stargazer: *
#set text(font: (
(name: "libertinus serif", covers: "latin-in-cjk"),
"Noto Sans CJK SC"
))
#show: stargazer-theme.with(
aspect-ratio: "16-9",
config-info(
    title: [{final_title}],
    logo: emoji.school,
),
config-common(slide-level: 3)
)
#title-slide()
{result}"""
    elif theme == 'aqua':
        result = f"""#import "@preview/touying:0.6.0": *
#import themes.aqua: *
#set text(font: (
(name: "libertinus serif", covers: "latin-in-cjk"),
"Noto Sans CJK SC"
))
#show: aqua-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [{final_title}],
  ),
  config-common(slide-level: 3)
)
#title-slide()
{result}
"""
    elif theme == 'university':
        result = f"""#import "@preview/touying:0.6.0": *
#import themes.university: *
#set text(font: (
(name: "libertinus serif", covers: "latin-in-cjk"),
"Noto Sans CJK SC"
))
#show: university-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [{final_title}],
    logo: emoji.school,
  ),
  config-common(slide-level: 3)
)
#title-slide()
{result}"""
    elif theme == 'dewdrop':
        result = f"""#import "@preview/touying:0.6.0": *
#import themes.dewdrop: *
#set text(font: (
(name: "libertinus serif", covers: "latin-in-cjk"),
"Noto Sans CJK SC"
))
#show: dewdrop-theme.with(
  aspect-ratio: "16-9",
  navigation: "mini-slides",
  config-info(
    title: [{final_title}],
  ),
  config-common(slide-level: 3)
)
#title-slide()
{result}"""
    elif theme == 'metropolis':
        result = f"""#import "@preview/touying:0.6.0": *
#import themes.metropolis: *
#set text(font: (
(name: "libertinus serif", covers: "latin-in-cjk"),
"Noto Sans CJK SC"
))
#show: metropolis-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: [{final_title}],
    logo: emoji.city,
  ),
  config-common(slide-level: 3)
)
#title-slide()
{result}"""
    return result

def convert_to_pptx(input_file, do_parse=True, theme='stargazer'):
    output_typ_file = f'{input_file}ppt.typ'
    output_md_file = f'{input_file}ppt.md'
    if do_parse:
        finalcontent = ''
        final_title = ''
        contents = parse_markdown(input_file)
        for content, title in contents:
            finalcontent = content
            final_title = title
            yield content
        with open(output_md_file, 'w', encoding='utf-8') as f:
            f.write(finalcontent)
        result = subprocess.run(
            ['pandoc', '-f', 'markdown', '-t', 'typst', output_md_file],
            capture_output=True,
            text=True).stdout
        result = get_template(theme, final_title, result)
        result = re.sub(r'<.*?>', '', result)
        with open(output_typ_file, 'w', encoding='utf-8') as f:
            f.write(result)
        os.remove(output_md_file)
    else:
        with open(output_typ_file, 'r', encoding='utf-8') as f:
            temp_result = f.read()
        header, result = temp_result.split('#title-slide()')
        final_title = re.findall(r'title: \[(.*?)\]', header)[0]
        result = get_template(theme, final_title, result)
        with open(output_typ_file, 'w', encoding='utf-8') as f:
            f.write(result)
    subprocess.run(['./typst', 'compile', output_typ_file])
