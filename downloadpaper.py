from scihub import SciHub
from chat import chatbot
from omniparse import parseDocument
import os
import arxiv

sh = SciHub()


def downloadDOIPaper(unknown):
    paperbot = chatbot()
    result = sh.download(f'{unknown}', path='./paper/temporaryPaper.pdf')
    text = parseDocument('temporaryPaper.pdf')
    title = paperbot.chat(f"下面是一篇论文的前255个字符，请返回该论文的标题：\n{text[:255]}")
    os.rename('paper/temporaryPaper.pdf', f'paper/{title.strip()}.pdf')


def downloadArxivPaper(arxivID):
    paperbot = chatbot()
    paper = next(arxiv.Client().results(arxiv.Search(id_list=[f"{arxivID}"])))
    # Download the PDF to a specified directory with a custom filename.
    paper.download_pdf(dirpath="./paper", filename="temporaryPaper.pdf")
    text = parseDocument('temporaryPaper.pdf')
    title = paperbot.chat(f"下面是一篇论文的前255个字符，请返回该论文的标题：\n{text[:255]}")
    os.rename('paper/temporaryPaper.pdf', f'paper/{title.strip()}.pdf')
