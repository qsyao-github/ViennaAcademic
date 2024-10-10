from omniparse import parseDocument
import os
import arxiv
from openai import OpenAI

client = OpenAI(api_key="sk-114514",
                base_url="https://1919810.com/v1")


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
        print('startParsing')
        text = parseDocument('./paper/temporaryPaper.pdf')
        print('parsingDone')
        title = title_generate(f"下面是论文节选，请提取论文标题，不要返回其它内容：\n{text[:255]}")
        abstract = text[text.find('Abstract') + 9:][:text.find('\n')]
        abstract = title_generate(f"将论文摘要译为中文，不要返回其它内容：\n{abstract}")
        with open(f'knowledgeBase/{title.strip()}.md', mode='w') as f:
            f.write(text)
        os.rename('./paper/temporaryPaper.pdf', f'./paper/{title.strip()}.pdf')
