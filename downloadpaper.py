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
    with libreq.urlopen(f'http://export.arxiv.org/api/query?id_list={arxivID}') as url:
        r = url.read().decode('utf-8')
    root = ET.fromstring(r)
    prefix = "{http://www.w3.org/2005/Atom}"
    entry = root.find(prefix+'entry')
    return entry.find(prefix+'title').text.replace("\n",""), entry.find(prefix+'summary').text.replace("\n",""), entry.find(prefix+'link').get('href').replace('abs','src')


def getTranslation(title, abstract):
    translated_title = query(f"将下列论文标题译为中文，不要返回除标题以外的其它内容：\n{title}")
    translated_abstract = query(f"将下列论文摘要译为中文，不要返回除摘要以外的其它内容：\n{abstract}")
    return translated_title, translated_abstract


def downloadArxivPaper(arxivID):
    try:
        title, abstract, link = getInformation(arxivID)
    except:
        return "ID可能错误"
    if f"{title}.tar.gz" not in os.listdir("arxivSource"):
        translated_title, translated_abstract = getTranslation(title, abstract)
        os.mkdir(f"arxivSource/{title}")
        os.chdir(f"arxivSource")
        curl = f'curl -L {link} -o "{title}.tar.gz"'
        subprocess.run(curl,shell=True,text=True,capture_output=True)
        subprocess.run(f'tar -I pigz -xf "/home/laowei/ViennaAcademic/arxivSource/{title}.tar.gz" -C "{title}"',shell=True,text=True,capture_output=True)
        os.chdir("..")
    os.chdir(f"arxivSource/{title}")
    # find main file
    mainFile= subprocess.run(f'grep -l "\\documentclass" *.tex',shell=True,text=True,capture_output=True)
    mainFile=mainFile.stdout.strip(" \n")
    # find sty file
    styFiles = [file.strip(".sty") for file in os.listdir() if file.endswith(".sty")]
    # find lines in mainFile with filename in styFiles, and comment the lines
    with open(mainFile, "r") as f:
        lines = f.readlines()
    lines = [("% "+line if any(file in line and '\\usepackage' in line for file in styFiles) else line) for line in lines]
    with open(mainFile, "w") as f:
        f.writelines(lines)
    # get bibliographies
    bibFiles = [f"--bibliography={file}" for file in os.listdir() if file.endswith(".bib")]
    subprocess.run(f'pandoc --wrap=none --standalone {" ".join(bibFiles)} --citeproc -f latex -t markdown "{mainFile}" -o "/home/laowei/ViennaAcademic/knowledgeBase/{title}.md"',shell=True,text=True,capture_output=True)
    os.chdir("/home/laowei/ViennaAcademic")
    try:
        return f"标题：{translated_title}\n\n摘要：\n{translated_abstract}"
    except:
        return f"文件可能已经存在\n\n标题：{title}\n\n摘要：\n{abstract}"
