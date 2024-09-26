from omniparse import parseDocument
import os
import arxiv
import ollama


def title_generate(prompt):
    answer = ""
    stream = ollama.chat(
        model='glm4',
        messages=[{
            'role': 'user',
            'content': prompt
        }],
        stream=True,
    )
    for chunk in stream:
        chunks = chunk['message']['content']
        print(chunks, end='', flush=True)
        answer += chunks
    return answer


def downloadArxivPaper(arxivID):
    paper = next(arxiv.Client().results(arxiv.Search(id_list=[f"{arxivID}"])))
    # Download the PDF to a specified directory with a custom filename.
    paper.download_pdf(dirpath="paper", filename="temporaryPaper.pdf")
    text = parseDocument('./paper/temporaryPaper.pdf')
    title = title_generate(f"下面是论文节选，请返回该论文的标题：\n{text[:255]}")
    os.rename('./paper/temporaryPaper.pdf', f'./paper/{title.strip()}.pdf')
    os.remove('./paper/temporaryPaper.txt')
