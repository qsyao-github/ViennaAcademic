from modelclient import client1, client4, client2, client5
from perplexica import deepAcademicSearch
import concurrent.futures
import time
from crawler import crawl_and_save
from downloadpaper import downloadArxivPaper
import asyncio
import math
from bceInference import update, get_response
import re


def deepseek_r1_query(messages):
    response = client1.chat.completions.create(
        model="deepseek-r1-distill-llama-70b",
        messages=messages,
        temperature=0.6)
    response = response.choices[0].message.content
    index = response.rfind(r'</think>')
    if index != -1:
        response = response[index + 8:]
    return response.strip()


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
    return response


def glm_query(system, query):
    response = client2.chat.completions.create(model='glm-4-flash',
                                               messages=[{
                                                   'role': "system",
                                                   "content": system
                                               }, {
                                                   'role': "user",
                                                   "content": query
                                               }])
    return response.choices[0].message.content


def perform_search(answer):
    print('\n'.join(answer))
    future_results = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for query in answer:
            print(query.strip('- *'))
            future_results.append(
                executor.submit(deepAcademicSearch, query.strip('- *')))
            time.sleep(1)
        results = [future.result() for future in future_results]
    message = '\n\n---\n\n'.join([result[0] for result in results])
    simplify_prompt = f"""Given the following contents from the queries:
{'\n'.join(answer)}
generate a markdown list of learnings from the contents. Return a maximum of 3 learnings for each query, but feel free to return less if the contents are clear. Make sure each learning is unique and not similar to each other. The learnings should be concise and to the point, as detailed and information dense as possible. Make sure to include any entities like people, places, companies, products, things, etc in the learnings, as well as any exact metrics, numbers, or dates. The learnings will be used to research the topic further.
"""
    learnings = glm_query(simplify_prompt, message)
    print(learnings)
    sourcesList = sum([result[1] for result in results], [])
    return message, sourcesList, learnings


def goal_and_future_directions(messages):
    messages.append({
        "role":
        "user",
        "content":
        "Talk about the goal of the research that these queries is meant to accomplish."
    })
    goal = deepseek_r1_query(messages)
    print(goal)
    messages[-1] = {
        "role":
        "user",
        "content":
        "Go deeper into how to advance the research once the results are found, mention additional research directions. Be as specific as possible."
    }
    future_directions = deepseek_r1_query(messages)
    print(future_directions)
    return goal, future_directions


def generate_query(query, breadth, learnings):
    list_generation_prompt = f"Given the following prompt from the user, generate a markdown unordered list of keywords(in English) to research the topic. Return a maximum of {breadth} queries, but feel free to return less if the original prompt is clear. Make sure each query is unique and not similar to each other.\n{query}" + (
        f"""\nHere are some learnings from previous research, use them to generate more specific and less repetitive queries.\n{'\n'.join(learnings)}"""
        if learnings else '')
    search_list = deepseek_r1_query([{
        "role": "user",
        "content": list_generation_prompt
    }])
    search_list = [item for item in search_list.split('\n') if item.startswith('- ')][:breadth]
    print(search_list)
    input()
    messages = [{
        "role": "user",
        "content": list_generation_prompt
    }, {
        "role": "assistant",
        "content": '\n'.join(search_list)
    }]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_search_result = executor.submit(perform_search, search_list)
        future_goal_and_directions = executor.submit(
            goal_and_future_directions, messages)
        message, sourcesList, learnings = future_search_result.result()
        goal, future_directions = future_goal_and_directions.result()
    new_query = f'Previous research goal: {goal}\nFollow-up research directions: {future_directions}'
    return message, sourcesList, learnings, new_query


def research(query, depth=2, breadth=4):
    if not 0 < breadth < 5:
        breadth = 4
    if not 0 < depth < 4:
        depth = 2
    research_result = []
    sources = []
    learnings = []
    while depth > 0:
        message, sourcesList, newlearnings, new_query = generate_query(
            query, breadth, learnings)
        research_result.append(message)
        sources.extend(sourcesList)
        learnings.append(newlearnings)
        query = new_query
        depth -= 1
        breadth = math.ceil(breadth / 2)
        print(message)
        print(len(message))
        input()
        print(sources)
        print(len(sources))
        input()
        print(learnings)
        input()
        print(query)
        input()
        print(depth, breadth)
        input('critical check point')
    return research_result, sources


'''research_result, sources = research("大数据处理技术理论综述报告", 3, 4)
# 将research_result, sources保存到文件中
with open('research_result.txt', 'w', encoding='utf-8') as f:
    for item in research_result:
        f.write(f"{item}\n")
with open('sources.txt', 'w', encoding='utf-8') as f:
    f.write(str(sources))
'''

def write_to_file(content, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
with open('research_result.txt','r', encoding='utf-8') as f:
    research_result = f.read()

with open('sources.txt','r', encoding='utf-8') as f:
    # 将文本解析为列表
    sources = eval(f.read())


def handle_reference(references):
    crawl_dict = {}
    for i in range(len(references)):
        entry = references[i]
        index = str(i + 1)
        pageContent, link = entry["pageContent"], entry["metadata"]["url"]
        filePath = f'knowledgeBase/STORMtemp{index}.md'
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


def generate_outline(summary, topic, chinese=True):
    prompt = f"你是一位文本大纲生成专家，擅长根据用户提供的信息创建一个有条理且易于扩展成完整文章的大纲，你拥有强大的主题分析能力，能准确提取关键信息和核心要点。具备丰富的文案写作知识储备，熟悉学术论文大纲构建方法，能够生成具有针对性、逻辑性和条理性的文案大纲，并且能确保大纲结构合理、逻辑通顺。你将撰写一篇学术文章，标题为：{topic}。根据用户提供的信息用markdown无序列表写出提纲(包括引言、结论)" if chinese else f"You are a text outline generation expert, skilled at creating a structured and easily expandable outline for a complete article based on the information provided by the user. You possess strong thematic analysis abilities, allowing you to accurately extract key information and core points. With a rich knowledge base in copywriting and familiarity with academic paper outline construction methods, you can generate targeted, logical, and coherent outlines while ensuring that the structure is reasonable and the logic flows smoothly. You will write an academic article titled: {topic}. Based on the information provided by the user, create an outline (including introduction and conclusion, no more than 5 sections). Use markdown syntax for headings. List corresponding paragraphs' subheadings for each section using markdown unordered lists. Each item corresponds to a paragraph, no sub-items."
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
        if line.strip() and (line.startswith('#') or line.startswith('- '))
    ])
    return response.strip()


print(generate_outline(research_result, "大数据处理技术理论综述报告"))
input()
handle_reference(sources)
