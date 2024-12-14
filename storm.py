import os
import json
from dspy import Example
from knowledge_storm.lm import OpenAIModel
from knowledge_storm.rm import SearXNG
from knowledge_storm import STORMWikiRunnerArguments, STORMWikiRunner, STORMWikiLMConfigs
import shutil
import re
from modelclient import Client1API_KEY, Client1BASE_URL


def main(topic,max_conv_turn=3, max_perspective=3, search_top_k=3, max_thread_num=1):
    lm_configs = STORMWikiLMConfigs()
    openai_kwargs = {
        'api_key': Client1API_KEY,
        'api_base': Client1BASE_URL,
        'temperature': 1.0,
        'top_p': 0.9
    }

    ModelClass = OpenAIModel
    gpt_35_model_name = 'claude-3-haiku'
    gpt_4_model_name = 'glm-4-flash'
    conv_simulator_lm = ModelClass(model=gpt_35_model_name, max_tokens=500, **openai_kwargs)
    question_asker_lm = ModelClass(model=gpt_35_model_name, max_tokens=500, **openai_kwargs)
    outline_gen_lm = ModelClass(model=gpt_4_model_name, max_tokens=400, **openai_kwargs)
    article_gen_lm = ModelClass(model=gpt_4_model_name, max_tokens=700, **openai_kwargs)
    article_polish_lm = ModelClass(model=gpt_4_model_name, max_tokens=4000, **openai_kwargs)
    lm_configs.set_conv_simulator_lm(conv_simulator_lm)
    lm_configs.set_question_asker_lm(question_asker_lm)
    lm_configs.set_outline_gen_lm(outline_gen_lm)
    lm_configs.set_article_gen_lm(article_gen_lm)
    lm_configs.set_article_polish_lm(article_polish_lm)
    engine_args = STORMWikiRunnerArguments(
        output_dir='storm',
        max_conv_turn=max_conv_turn,
        max_perspective=max_perspective,
        search_top_k=search_top_k,
        max_thread_num=max_thread_num,
    )
    def contains_chinese_characters(s):
        # 使用正则表达式匹配中文字符
        pattern = re.compile(r'[\u4e00-\u9fa5]')
        return bool(pattern.search(s))

    # STORM is a knowledge curation system which consumes information from the retrieval module.
    # Currently, the information source is the Internet and we use search engine API as the retrieval module.
    rm = SearXNG(searxng_api_url='http://localhost:4000', k=engine_args.search_top_k)
    runner = STORMWikiRunner(engine_args, lm_configs, rm)
    if not contains_chinese_characters(topic):
        print('English')
        # 下面是一段python代码，保持格式、语法不变，将其中的英文字符串译为中文：
        find_related_topic_example = Example(
            topic="Knowledge Curation",
            related_topics="https://en.wikipedia.org/wiki/Knowledge_management\n"
                        "https://en.wikipedia.org/wiki/Information_science\n"
                        "https://en.wikipedia.org/wiki/Library_science\n"
        )
        gen_persona_example = Example(
            topic="Knowledge Curation",
            examples="Title: Knowledge management\n"
                    "Table of Contents: History\nResearch\n  Dimensions\n  Strategies\n  Motivations\nKM technologies"
                    "\nKnowledge barriers\nKnowledge retention\nKnowledge audit\nKnowledge protection\n"
                    "  Knowledge protection methods\n    Formal methods\n    Informal methods\n"
                    "  Balancing knowledge protection and knowledge sharing\n  Knowledge protection risks",
            personas=(
                "1. Historian of Knowledge Systems: This editor will focus on the history and evolution of knowledge "
                "curation. They will provide context on how knowledge curation has changed over time and its impact on "
                "modern practices.\n"
                "2. Information Science Professional: With insights from 'Information science', this editor will "
                "explore the foundational theories, definitions, and philosophy that underpin knowledge curation\n"
                "3. Digital Librarian: This editor will delve into the specifics of how digital libraries operate, "
                "including software, metadata, digital preservation.\n"
                "4. Technical expert: This editor will focus on the technical aspects of knowledge curation, "
                "such as common features of content management systems.\n"
                "5. Museum Curator: The museum curator will contribute expertise on the curation of physical items and "
                "the transition of these practices into the digital realm."
            )
        )
        runner.storm_knowledge_curation_module.persona_generator.create_writer_with_persona.find_related_topic.demos = [
            find_related_topic_example]
        runner.storm_knowledge_curation_module.persona_generator.create_writer_with_persona.gen_persona.demos = [
            gen_persona_example]

        write_page_outline_example = Example(
            topic="Example Topic",
            conv="Wikipedia Writer: ...\nExpert: ...\nWikipedia Writer: ...\nExpert: ...",
            old_outline="# Section 1\n## Subsection 1\n## Subsection 2\n"
                        "# Section 2\n## Subsection 1\n## Subsection 2\n"
                        "# Section 3",
            outline="# New Section 1\n## New Subsection 1\n## New Subsection 2\n"
                    "# New Section 2\n"
                    "# New Section 3\n## New Subsection 1\n## New Subsection 2\n## New Subsection 3"
        )
        runner.storm_outline_generation_module.write_outline.write_page_outline.demos = [write_page_outline_example]
        write_section_example = Example(
            info="[1]\nInformation in document 1\n[2]\nInformation in document 2\n[3]\nInformation in document 3",
            topic="Example Topic",
            section="Example Section",
            output="# Example Topic\n## Subsection 1\n"
                "This is an example sentence [1]. This is another example sentence [2][3].\n"
                "## Subsection 2\nThis is one more example sentence [1]."
        )
    else:
        print('Chinese')
        find_related_topic_example = Example(
            topic="知识管理",
            related_topics="https://en.wikipedia.org/wiki/Knowledge_management\n"
                        "https://en.wikipedia.org/wiki/Information_science\n"
                        "https://en.wikipedia.org/wiki/Library_science\n"
        )
        gen_persona_example = Example(
            topic="知识管理",
            examples="标题: 知识管理\n"
                    "目录: 历史\n研究\n  维度\n  策略\n  动机\nKM 技术"
                    "\n知识障碍\n知识保留\n知识审计\n知识保护\n"
                    "  知识保护方法\n    正式方法\n    非正式方法\n"
                    "  平衡知识保护与知识共享\n  知识保护风险",
            personas=(
                "1. 知识系统历史学家: 该编辑将专注于知识管理的历史和演变。"
                "他们将提供关于知识管理如何随着时间变化及其对现代实践影响的背景。\n"
                "2. 信息科学专业人士: 通过'信息科学'的见解，该编辑将探讨支撑知识管理的基础理论、定义和哲学。\n"
                "3. 数字图书管理员: 该编辑将深入探讨数字图书馆的运作细节，包括软件、元数据、数字保存。\n"
                "4. 技术专家: 该编辑将专注于知识管理的技术方面，例如内容管理系统的常见特性。\n"
                "5. 博物馆策展人: 博物馆策展人将贡献在物理物品策展方面的专业知识，以及这些实践向数字领域的过渡。"
            )
        )
        runner.storm_knowledge_curation_module.persona_generator.create_writer_with_persona.find_related_topic.demos = [
            find_related_topic_example]
        runner.storm_knowledge_curation_module.persona_generator.create_writer_with_persona.gen_persona.demos = [
            gen_persona_example]
        write_page_outline_example = Example(
            topic="示例主题",
            conv="维基百科撰稿人: ...\n专家: ...\n维基百科撰稿人: ...\n专家: ...",
            old_outline="# 第一部分\n## 子部分 1\n## 子部分 2\n"
                        "# 第二部分\n## 子部分 1\n## 子部分 2\n"
                        "# 第三部分",
            outline="# 新部分 1\n## 新子部分 1\n## 新子部分 2\n"
                    "# 新部分 2\n"
                    "# 新部分 3\n## 新子部分 1\n## 新子部分 2\n## 新子部分 3"
        )
        runner.storm_outline_generation_module.write_outline.write_page_outline.demos = [write_page_outline_example]
        write_section_example = Example(
            info="[1]\n文档 1 中的信息\n[2]\n文档 2 中的信息\n[3]\n文档 3 中的信息",
            topic="示例主题",
            section="示例部分",
            output="# 示例主题\n## 子部分 1\n"
                "这是一个示例句子 [1]。这是另一个示例句子 [2][3]。\n"
                "## 子部分 2\n这是另一个示例句子 [1]。"
        )
    runner.storm_article_generation.section_gen.write_section.demos = [write_section_example]
    runner.run(
        topic=topic,
        do_research=True,
        do_generate_outline=True,
        do_generate_article=True,
        do_polish_article=True,
        remove_duplicate=False
    )
    runner.post_run()
    runner.summary()
def replaceSharpwithBullets(outlineList):
    for i in range(len(outlineList)):
        Sharpnum=outlineList[i].count('#')-1
        outlineList[i]='    '*Sharpnum+'- '+outlineList[i].lstrip('#').strip()
    return outlineList
def generate(topic, max_conv_turn=3, max_perspective=3, search_top_k=3, max_thread_num=1):
    if os.path.exists('storm'):
        shutil.rmtree('storm')
    os.mkdir('storm')
    main(topic,max_conv_turn, max_perspective, search_top_k, max_thread_num)
    topicDirList=topic.split(' ')
    os.chdir(rf'storm')
    for i in os.listdir():
        if all([j.lower() in i.lower() for j in topicDirList]):
            os.chdir(rf'{i}')
            break
    with open('storm_gen_outline.txt', 'r',encoding='utf-8',errors='replace') as f:
        outline = f.readlines()
    outlineList=replaceSharpwithBullets(outline)
    with open('storm_gen_article_polished.txt','r',encoding='utf-8',errors='replace') as f:
        article = f.read()
    # 提取url_to_info.json中的json，返回字典
    with open('url_to_info.json', 'r',encoding='utf-8',errors='replace') as f:
        url_to_info = json.load(f)
    url_to_index=url_to_info["url_to_unified_index"]
    url_to_detailed_info=url_to_info["url_to_info"]
    all_reference_list=[(value,key) for key,value in url_to_index.items()]
    all_reference_list.sort(key=lambda x:x[0])
    reference_list=[f'[{item[0]}]: [{url_to_detailed_info[item[1]]["title"]}]({item[1]})' for item in all_reference_list]
    reference='\\\n'.join(reference_list)
    finalArticle='\n'.join(outlineList)+'\n\n'+article+'\n\n'+reference
    os.chdir(rf'../..')
    return finalArticle

# C:\Users\15081\miniconda3\envs\viennaac_venv\Lib\site-packages\knowledge_storm\utils.py
