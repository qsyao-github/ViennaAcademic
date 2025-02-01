import os
import subprocess
from modelclient import client1 as client
import urllib.request as libreq
import xml.etree.ElementTree as ET


def query(prompt):
    response = client.chat.completions.create(model="gpt-4o-mini",
                                              messages=[{
                                                  "role": "user",
                                                  "content": prompt
                                              }])
    return response.choices[0].message.content


def getInformation(arxivID):
    with libreq.urlopen(
            f'http://export.arxiv.org/api/query?id_list={arxivID}') as url:
        r = url.read().decode('utf-8')
    root = ET.fromstring(r)
    prefix = "{http://www.w3.org/2005/Atom}"
    entry = root.find(prefix + 'entry')
    return entry.find(prefix + 'title').text.replace(
        "\n", ""), entry.find(prefix + 'summary').text.replace(
            "\n",
            ""), entry.find(prefix + 'link').get('href').replace('abs', 'src')


def getTranslation(title, abstract):
    translated_title = query(f"将下列论文标题译为中文，不要返回除标题以外的其它内容：\n{title}")
    translated_abstract = query(f"将下列论文摘要译为中文，不要返回除摘要以外的其它内容：\n{abstract}")
    return translated_title, translated_abstract


def findMainFile():
    grep = f'grep -l "^[^%]*\\documentclass" *.tex'
    mainFile = subprocess.run(grep, shell=True, text=True, capture_output=True)
    return mainFile.stdout.strip(" \n")


def commentUsePackage(mainFile, styFiles):
    with open(mainFile, "r") as f:
        lines = f.readlines()
    lines = [("% " + line if any(file in line and '\\usepackage' in line
                                 for file in styFiles) else line)
             for line in lines]
    with open(mainFile, "w") as f:
        f.writelines(lines)


def downloadArxivPaper(arxivID, storm=False, index=None):
    try:
        title, abstract, link = getInformation(arxivID)
    except:
        return "ID可能错误"
    if f"{title}.tar.gz" not in os.listdir("arxivSource"):
        if not storm:
            translated_title, translated_abstract = getTranslation(
                title, abstract)
        else:
            title = "STORMtemp" + index
        targetDir = f"arxivSource/{title}"
        os.mkdir(targetDir)
        os.chdir(f"arxivSource")
        try:
            curl = f'curl -L {link} -o "{title}.tar.gz"'
            subprocess.run(curl, shell=True, text=True, capture_output=True)
            pigz = f'tar -I pigz -xf "/home/laowei/ViennaAcademic/arxivSource/{title}.tar.gz" -C "{title}"'
            subprocess.run(pigz, shell=True, text=True, capture_output=True)
        except:
            os.chdir("..")
            return "没有源文件"
        os.chdir("..")
    os.chdir(targetDir)
    # find main file
    mainFile = findMainFile()
    # find sty file
    styFiles = [
        file.strip(".sty") for file in os.listdir() if file.endswith(".sty")
    ]
    # find lines in mainFile with filename in styFiles, and comment the lines
    commentUsePackage(mainFile, styFiles)
    # get bibliographies
    bibFiles = [
        f"--bibliography={file}" for file in os.listdir()
        if file.endswith(".bib")
    ]
    pandoc = f'pandoc --wrap=none --standalone {" ".join(bibFiles)} --citeproc -f latex -t markdown "{mainFile}" -o "/home/laowei/ViennaAcademic/knowledgeBase/{title}.md"'
    subprocess.run(pandoc, shell=True, text=True, capture_output=True)
    os.chdir("/home/laowei/ViennaAcademic")
    try:
        return f"标题：{translated_title}\n\n摘要：\n{translated_abstract}"
    except:
        return f"文件可能已经存在\n\n标题：{title}\n\n摘要：\n{abstract}"
