from crawler import crawl_and_save
from bceInference import update, get_response
from downloadpaper import downloadArxivPaper
from modelclient import client1, client2, client5
from deepresearch import research
import re
import os
import time
from datetime import datetime
import threading
import asyncio
import concurrent.futures

def write_to_file(content, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
def handle_reference(references):
    crawl_dict = {}
    for i in range(len(references)):
        entry = references[i]
        index = str(i+1)
        pageContent, link = entry["pageContent"], entry["metadata"]["url"]
        filePath=f'knowledgeBase/STORMtemp{index}.md'
        if 'http://arxiv.org/abs/' in link:
            arxivID = link.split('/')[-1]
            if 'v' in arxivID:
                arxivID = arxivID.split('v')[0]
            if '.' in arxivID:
                result = downloadArxivPaper(arxivID, True, index)
                if result == "ID可能错误":
                    content = pageContent
                else:
                    content = ''
            else:
                content = pageContent
        elif link.endswith('.pdf'):
            content = pageContent
        else:
            crawl_dict[link] = filePath
            content = pageContent + '\n###### \n'
        if content:
            write_to_file(content, filePath)
    asyncio.run(crawl_and_save(crawl_dict))
    update()


def delete_temp_files():
    for folder in ['knowledgeBase', 'retrievers']:
        for file in os.listdir(folder):
            if file.startswith('STORMtemp'):
                os.remove(f'{folder}/{file}')


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

def deepseek_chat(system, query):
    response = client1.chat.completions.create(model="deepseek-ai/DeepSeek-V3",
                                               messages=[{
                                                   "role": "system",
                                                   "content": system
                                               }, {
                                                   "role": "user",
                                                   "content": query
                                               }])
    return response.choices[0].message.content
def silicon_chat(system, query):
    messages = [{
        "role": "system",
        "content": system
    }, {
        "role": "user",
        "content": query
    }]
    response = client5.chat.completions.create(
        model="Pro/deepseek-ai/DeepSeek-V3",
        messages=messages)
    return response.choices[0].message.content
def mixed_chat(system, query, thread_num):
    if thread_num == 1:
        return gpt_chat(system, query)
    else:
        return silicon_chat(system, query)

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

"""你是一位文本大纲生成专家，擅长根据用户提供的信息创建一个有条理且易于扩展成完整文章的大纲，你拥有强大的主题分析能力，能准确提取关键信息和核心要点。具备丰富的文案写作知识储备，熟悉学术论文大纲构建方法，能够生成具有针对性、逻辑性和条理性的文案大纲，并且能确保大纲结构合理、逻辑通顺。"""
def generate_outline(summary, topic, chinese=True):
    prompt = f"你是一位文本大纲生成专家，擅长根据用户提供的信息创建一个有条理且易于扩展成完整文章的大纲，你拥有强大的主题分析能力，能准确提取关键信息和核心要点。具备丰富的文案写作知识储备，熟悉学术论文大纲构建方法，能够生成具有针对性、逻辑性和条理性的文案大纲，并且能确保大纲结构合理、逻辑通顺。你将撰写一篇学术文章，主题为：{topic}。根据用户提供的信息用markdown无序列表写出提纲(包括引言、结论)" if chinese else f"You are a text outline generation expert, skilled at creating a structured and easily expandable outline for a complete article based on the information provided by the user. You possess strong thematic analysis abilities, allowing you to accurately extract key information and core points. With a rich knowledge base in copywriting and familiarity with academic paper outline construction methods, you can generate targeted, logical, and coherent outlines. You will ensure that the outline structure is reasonable and the logic flows smoothly. You will write an academic article titled: {topic}. Based on the information provided by the user, write the outline in markdown unordered list format (including introduction and conclusion)."
    response = silicon_chat(prompt, summary)
    response = response.strip('`')
    response = response[response.find('#'):]
    for keyword in [
            '关键词', 'keyword', 'Keyword', 'Reference', 'reference', '参考文献'
    ]:
        if keyword in response:
            response = response.split(keyword)[0].rstrip(' \n#*')
    response = re.sub(r'\d+\.\s+|\d+\.\d+\s+', '', response)
    response = '\n'.join([
        line for line in response.split('\n')
        if line.strip() if line.startswith('#') or line.startswith('- ')])
    return response.strip()


def write_paragraph(outlines, i, subtitle, subtopic, title, level, chinese=True, thread_num=0):
    reference = get_response(f"{title}: {subtopic}").strip()
    if reference:
        prompt = f'你将撰写一个段落，主题为{subtopic}，该段落属于一题目为“{title}”的学术文章的“{subtitle}”部分。请参考相关文献结合自身理解撰写，引用部分以"【编号】"形式注明出处。使用中文。' if chinese else f'''You're about to write ONE paragraph about {subtopic}, which belongs to the "{subtitle}" part of an academic article named "{title}". Please integrate related literatures and your understanding, and cite the source as "[number]".'''
        response = mixed_chat(prompt, reference, thread_num)
    else:
        if chinese:
            response = mixed_chat(f'你将撰写一个段落，主题为{subtopic}，该段落属于一题目为“{title}”的学术文章的“{subtitle}”部分。', '请结合自身理解撰写该段落，不要编造。使用中文', thread_num)
        else:
            response = mixed_chat(f'You are about to write ONE paragraph about {subtopic}, which belongs to the "{subtitle}" part of an academic article named "{title}".', 'Integrate your own understanding in the paragraph. Do not hallucinate.', thread_num)
    response_check = re.split('\n+',response.strip())
    response = f"{'#' * level}# {subtopic}\n\n{max(response_check, key=len)}"
    outlines[i] = response


# 定义一个函数，用于写入段落
def write_paragraphs(list_of_tasks, thread_num):
    for task in list_of_tasks:
        write_paragraph(*task, thread_num)
    return

def parse_outline(outline, title, chinese=True):
    outlines = re.split(r'\n+', outline.strip())
    current_subtitle = ''
    current_subtopic = ''
    tasks = []
    level = 1
    for i, line in enumerate(outlines):
        if line and line.startswith('#'):
            current_subtitle = line.strip('#').strip()
            level = len(line) - len(line.strip('#'))
        if line and line.startswith('-'):
            current_subtopic = line.strip('-').strip()
            tasks.append((outlines, i, current_subtitle, current_subtopic, title, level, chinese))
    length = len(tasks)
    # num_threads = min(length, 4)
    threads = []
    for i in range(4):
        if i == 0:
            start_index = int(i * length / 5)
            end_index = int((i+1) * length / 5)
        elif i == 1:
            start_index = int(i * length / 5)
            end_index = int((i+2) * length / 5)
        else:
            start_index = int((i+1) * length / 5)
            end_index = int((i+2) * length / 5)
        subtasks = tasks[start_index:end_index]
        t = threading.Thread(target=write_paragraphs, args=(subtasks, i%4))
        threads.append(t)
        t.start()
    while any(thread.is_alive() for thread in threads):
        yield '\n\n'.join(outlines)
        time.sleep(1)
    for t in threads:
        t.join()
    yield '\n\n'.join(outlines)


def isChinese(query):
    return any('\u4e00' <= char <= '\u9fff' for char in query)


def organize_outline(outline):
    outlines = re.split(r'\n+', outline.strip())
    current_level = 0
    for i, line in enumerate(outlines):
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
            abstract = abstract.split('摘要')[1].strip(' \n:：')
    else:
        abstract = mistral_chat(
            "You are an academic article author. Please write an abstract for your article.",
            article)
        for keyword in ['abstract', 'Abstract']:
            if keyword in abstract:
                abstract = abstract.split(keyword, 1)[1].strip(' \n:*')
                break
    return abstract


def generate(query, depth = 2, breadth = 2):
    delete_temp_files()
    chinese = isChinese(query)
    researchIter = research(query, depth, breadth)
    summary, reference = "", []
    for temp_result in researchIter:
        summary, reference = temp_result
        yield temp_result[0]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.submit(handle_reference, reference)
        future_outline = executor.submit(generate_outline, summary, query, chinese)
        outline = future_outline.result()
    yield outline
    articleGenerator = parse_outline(outline, query, chinese)
    for tempArticle in articleGenerator:
        article = tempArticle
        yield article
    outline = organize_outline(outline)
    abstract = write_abstract(article, chinese)
    article = re.sub(r'\n',
                     ('\n\n##### 摘要\n\n' if chinese else '\n\n### Abstract\n\n') +
                     abstract + '\n',
                     article,
                     count=1)
    yield article
    current_date = datetime.now()
    formatted_date = current_date.strftime('%Y-%m-%d')
    if not chinese:
        referenceStr = [f'[{i+1}] "{ref['metadata']['title']}." Accessed: {formatted_date}. [Online]. Available: {ref['metadata']['url']}' for i, ref in enumerate(reference)]
    else:
        referenceStr = [f'[{i+1}] {ref['metadata']['title']}[EB/OL].[{formatted_date}]. {ref['metadata']['url']}' for i, ref in enumerate(reference)]
    finalVersion = outline.lstrip() + '\n\n' + article + (
        '\n\n## 参考文献\n\n' if chinese else '\n\n## References\n\n') + '\n\n'.join(referenceStr)
    delete_temp_files()
    yield finalVersion
# ppt
def _extract_content(contentList, prompt, tasks, thread_num):
    for task in tasks:
        bullets = mixed_chat(prompt, task[1], thread_num)
        bullets = max(re.split('\n+',bullets.strip()), key=len)
        contentList[task[0]] = task[2] + bullets
    return


def extract_content(content, chinese=True):
    prompt = ("你是经验丰富的ppt制作人，根据演讲稿制作PPT，用语精炼，返回markdown无序列表，一级条目总数不超过3。不要返回其他内容。" if chinese else
                              "You are an experienced PPT creator. Based on the presentation script, create a PPT with concise language, and return a markdown unordered list. The number of top-level items should not exceed 3. Do not return any other content.")
    contentList = re.split(r'\n+', content.strip())
    title = contentList[0].strip('#').strip()
    contentList[0] = ''
    tasks = []
    abstract_index = contentList.index('##### 摘要')
    if abstract_index == -1:
        abstract_index = contentList.index('##### Abstract')
    if abstract_index != -1:
        contentList[abstract_index] = ''
        contentList[abstract_index + 1] = ''
    for i, line in enumerate(contentList[1:]):
        line = line.strip()
        if line.startswith('#'):
            contentList[i+1] = line[1:]
        elif line:
            tasks.append((i+1, f"{line}\n\n", ""))
    length = len(tasks)
    # num_threads = min(length, 4)
    threads = []
    for i in range(4):
        if i == 0:
            start_index = int(i * length / 5)
            end_index = int((i+1) * length / 5)
        elif i == 1:
            start_index = int(i * length / 5)
            end_index = int((i+2) * length / 5)
        else:
            start_index = int((i+1) * length / 5)
            end_index = int((i+2) * length / 5)
        subtasks = tasks[start_index:end_index]
        t = threading.Thread(target=_extract_content, args=(contentList, prompt, subtasks, i%4))
        threads.append(t)
        t.start()
    while any(thread.is_alive() for thread in threads):
        yield '\n\n'.join(contentList), title
        time.sleep(1)
    for t in threads:
        t.join()
    yield '\n\n'.join(contentList), title
