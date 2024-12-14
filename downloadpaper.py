from doclingParse import parseEverything
import os
import arxiv
from openai import OpenAI
from modelclient import client1 as client


def title_generate(prompt):
    response = client.chat.completions.create(model="gpt-4o-mini",
                                              messages=[{
                                                  "role": "user",
                                                  "content": prompt
                                              }])
    return response.choices[0].message.content


def downloadArxivPaper(arxivID):
    if arxivID:
        paper = next(arxiv.Client().results(
            arxiv.Search(id_list=[f"{arxivID}"])))
        # Download the PDF to a specified directory with a custom filename.
        paper.download_pdf(dirpath="paper", filename="temporaryPaper.pdf")
        text = parseEverything('./paper/temporaryPaper.pdf')
        try:
            title = title_generate(f"下面是论文节选，请提取论文标题，不要返回其它内容：\n{text[:255]}")
        except:
            title = arxivID
        try:
            abstractStart=text.find('Abstract')
            if abstractStart!=-1:
                abstract = text[text.find('Abstract') + 9:][:text.find('\n')]
                abstract = title_generate(f"将论文摘要译为中文，不要返回其它内容：\n{abstract}")
            else:
                abstract = "摘要识别失败"
        except:
            abstract = "摘要识别失败"
        os.remove(r'paper\temporaryPaper.pdf')
        return title, abstract, text
