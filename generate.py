from doclingParse import parseWebsite
from perplexica import stormSearch
from qanythingClient import update, qanything_fetch
from downloadpaper import downloadArxivPaper, getInformation
from modelclient import client1, client2
import re
import os
import time
import shutil


def handle_reference(references):
    for i in range(len(references)):
        entry = references[i]
        index = str(i+1)
        pageContent, link = entry["pageContent"], entry["metadata"]["url"]
        if 'http://arxiv.org/abs/' in link:
            arxivID = link.split('/')[-1]
            if 'v' in arxivID:
                arxivID = arxivID.split('v')[0]
            if '.' in arxivID:
                print(arxivID)
                try:
                    os.chdir('/home/laowei/ViennaAcademic')
                    print(downloadArxivPaper(arxivID, True, index))
                except:
                    os.chdir('/home/laowei/ViennaAcademic')
                    title, abstract, link = getInformation(arxivID)
                    with open(f'knowledgeBase/STORMtemp{index}.md','w',encoding='utf-8') as f:
                        f.write(pageContent + '\n###### \n' + abstract)
            else:
                os.chdir('/home/laowei/ViennaAcademic')
                with open(f'knowledgeBase/STORMtemp{index}.md','w',encoding='utf-8') as f:
                    f.write(pageContent)
        else:
            print(link)
            try:
                os.chdir('/home/laowei/ViennaAcademic')
                with open(f'knowledgeBase/STORMtemp{index}.md',
                          'w',
                          encoding='utf-8') as f:
                    f.write(pageContent + '\n###### \n'+parseWebsite(link))
            except:
                os.chdir('/home/laowei/ViennaAcademic')
                with open(f'knowledgeBase/STORMtemp{index}.md',
                          'w',
                          encoding='utf-8') as f:
                    f.write(pageContent)
    update()


def delete_temp_files():
    for file in os.listdir('knowledgeBase'):
        if file.startswith('STORMtemp'):
            os.remove(os.path.join('knowledgeBase', file))
    for file in os.listdir('retrievers'):
        if file.startswith('STORMtemp'):
            os.remove(os.path.join('retrievers', file))
    # 移除arxivSource下开头为STORMtemp的文件，递归移除开头为STORMtemp的文件夹
    for root, dirs, files in os.walk('arxivSource'):
        for file in files:
            if file.startswith('STORMtemp'):
                os.remove(os.path.join(root, file))
        for dir in dirs:
            if dir.startswith('STORMtemp'):
                shutil.rmtree(os.path.join(root, dir))


def gpt_chat(system, query):
    start = time.time()
    response = client1.chat.completions.create(model="gpt-4o-mini",
                                               messages=[{
                                                   "role": "system",
                                                   "content": system
                                               }, {
                                                   "role": "user",
                                                   "content": query
                                               }])
    response = response.choices[0].message.content
    end = time.time()
    time.sleep(max(1, 10-(end-start)))
    return response


def glm_chat(system, query):
    response = client2.chat.completions.create(model="glm-4-flash",
                                               messages=[{
                                                   "role": "system",
                                                   "content": system
                                               }, {
                                                   "role": "user",
                                                   "content": query
                                               }])
    response = response.choices[0].message.content
    return response


def mistral_chat(system, query):
    response = client1.chat.completions.create(model="mistral-large-latest",
                                               messages=[{
                                                   "role": "system",
                                                   "content": system
                                               }, {
                                                   "role": "user",
                                                   "content": query
                                               }])
    response = response.choices[0].message.content
    return response


def generate_outline(summary, topic, chinese=True):
    if chinese:
        response = gpt_chat(
            f"你将撰写一篇学术文章，标题为：{topic}。根据用户提供的信息，用markdown标题写出提纲(包括引言、结论，不超过5部分)，并在每个标题下用markdown无序列表列出关键词，每个关键词将会被拓展为一段",
            summary)
    else:
        response = gpt_chat(
            f"You're about to write an article, with a title of: {topic}. Based on the information provided, write an outline with markdown headers(include Introduction and Conclusion, no more than 5 parts), and list some key words as a markdown unordered list under each heading, each key word will be expanded into a paragraph later.",
            summary)
    response = response[response.find('#'):]
    if '关键词' in response:
        response = response.split('关键词')[0].rstrip(' \n#*')
    if 'keyword' in response:
        response = response.split('keyword')[0].rstrip(' \n#*')
    if 'Keyword' in response:
        response = response.split('Keyword')[0].rstrip(' \n#*')
    if 'Reference' in response:
        response = response.split('Reference')[0].rstrip(' \n#*')
    if 'reference' in response:
        response = response.split('reference')[0].rstrip(' \n#*')
    if '参考文献' in response:
        response = response.split('参考文献')[0].rstrip(' \n#*')
    return response.strip()


def write_paragraph(subtitle, subtopic, title, chinese=True):
    if chinese:
        response = gpt_chat(
            f'你将撰写一个段落，主题为{subtopic}，该段落属于一题目为“{title}”的学术文章的“{subtitle}”部分。请参考相关文献结合自身理解撰写，引用部分通过"【编号】"注明出处。',
            qanything_fetch(title + "：" + subtopic))
    else:
        response = gpt_chat(
            f'''You're about to write ONE paragraph about {subtopic}, which belongs to the "{subtitle}" part of an academic article named "{title}". Please integrate related literatures and your understanding, and cite the source as "[number]".''',
            qanything_fetch(title + ": " + subtopic))
    return response


def parse_outline(outline, title, chinese=True):
    outlines = re.split(r'\n+', outline)
    current_subtitle = ''
    current_subtopic = ''
    for i in range(len(outlines)):
        line = outlines[i]
        if line and line.startswith('#'):
            current_subtitle = line.strip('#').strip()
        if line and line.startswith('-'):
            current_subtopic = line.strip('-').strip()
            draft = write_paragraph(current_subtitle, current_subtopic, title,
                                    chinese)
            print(draft)
            outlines[i] = f"{draft}"
    return '\n\n'.join(outlines)


def isChinese(query):
    return bool(re.search(r'[\u4e00-\u9fff]', query))


def organize_outline(outline):
    outlines = re.split(r'\n+', outline)
    current_level = 0
    for i in range(len(outlines)):
        line = outlines[i]
        if line and line.startswith('#'):
            current_level = line.count('#')
            line = re.sub(r'#+\s+', '    ' * (current_level - 1) + '- ', line)
        if line and line.startswith('-'):
            line = re.sub(r'-+\s+', '    ' * current_level + '- ', line)
        outlines[i] = line
    return '\n'.join(outlines)


def write_abstract(article, chinese=True):
    if chinese:
        abstract = glm_chat("你是一学术文章作者，为你写的文章撰写摘要", article)
        if '摘要' in abstract:
            abstract = abstract.split('摘要：')[1].strip(' \n:：')
    else:
        abstract = mistral_chat(
            "You are an academic article author. Please write an abstract for your article.",
            article)
        if 'abstract' in abstract:
            abstract = abstract.split('abstract:')[1].lstrip(' \n:*')
        elif 'Abstract' in abstract:
            abstract = abstract.split('Abstract:')[1].lstrip(' \n:*')
    return abstract


def generate(query):
    delete_temp_files()
    chinese = isChinese(query)
    summary, reference = stormSearch(query)
    handle_reference(reference)
    outline = generate_outline(summary, query, chinese)
    article = parse_outline(outline, query, chinese)
    outline = organize_outline(outline)
    abstract = write_abstract(article, chinese)
    article = re.sub(r'\n',
                     ('\n\n### 摘要\n\n' if chinese else '\n\n### Abstract\n\n') +
                     abstract + '\n',
                     article,
                     count=1)
    referenceStr = [f"[{i+1}] [{reference[i]['metadata']["title"]}]({reference[i]["metadata"]["url"]})" for i in range(len(reference))]
    finalVersion = outline.lstrip() + '\n\n' + article + (
        '\n\n## 参考文献\n\n' if chinese else '\n\n## References\n\n') + '\n\n'.join(referenceStr)
    delete_temp_files()
    return finalVersion
