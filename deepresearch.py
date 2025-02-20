from modelclient import client1, client4, client2
from perplexica import deepAcademicSearch
import concurrent.futures
import time
import math


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
    queries = answer.split('\n')
    future_results = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for query in queries:
            if query.startswith('- '):
                future_results.append(
                    executor.submit(deepAcademicSearch, query.strip('- ')))
                time.sleep(1)
        results = [future.result() for future in future_results]
    message = '\n\n---\n\n'.join([result[0] for result in results])
    simplify_prompt = f"""Given the following contents from the queries:
{'\n'.join([query for query in queries if query.startswith('- ')])}
generate a markdown list of learnings from the contents. Return a maximum of 3 learnings for each query, but feel free to return less if the contents are clear. Make sure each learning is unique and not similar to each other. The learnings should be concise and to the point, as detailed and information dense as possible. Make sure to include any entities like people, places, companies, products, things, etc in the learnings, as well as any exact metrics, numbers, or dates. The learnings will be used to research the topic further.
"""
    learnings = glm_query(simplify_prompt, message)
    print(learnings)
    input()
    for result in results:
        print(result[1])
        input()
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
    list_generation_prompt = f"Given the following prompt from the user, generate keywords to research the topic as a markdown unordered list. Return a maximum of {breadth} queries, but feel free to return less if the original prompt is clear. Make sure each query is unique and not similar to each other.\n{query}" + (
        f"""\nHere are some learnings from previous research, use them to generate more specific and less repetitive queries.\n{'\n'.join(learnings)}"""
        if learnings else '')
    search_list = deepseek_r1_query([{
        "role": "user",
        "content": list_generation_prompt
    }])
    print(search_list)
    input()
    messages = [{
        "role": "user",
        "content": list_generation_prompt
    }, {
        "role": "assistant",
        "content": search_list
    }]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_search_result = executor.submit(perform_search, search_list)
        future_goal_and_directions = executor.submit(goal_and_future_directions, messages)
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
        message, sourcesList, newlearnings, new_query = generate_query(query, breadth, learnings)
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



research("大数据处理技术理论综述报告", 3, 4)



"""

"""
