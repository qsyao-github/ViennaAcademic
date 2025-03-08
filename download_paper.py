from docling_parser import parse_arxiv
from modelclient import deepseek_v3
from langchain_core.prompts import ChatPromptTemplate
from typing import Tuple, Optional
import concurrent.futures
from academic_search import search_arxiv

translate_template = ChatPromptTemplate.from_messages(
    [
        ("system", "请将下列论文{type}译为中文，不要返回除{type}以外的其它内容"),
        ("user", "{content}"),
    ]
)


def get_information(arxiv_id: str) -> Tuple[str, str, str]:
    return search_arxiv(arxiv_id)[0]


def translate_title(title: str, storm: bool = False) -> str:
    if not storm:
        translate_title_prompt = translate_template.invoke(
            {"type": "标题", "content": title}
        )
        return deepseek_v3.invoke(translate_title_prompt).content
    return title


def translate_abstract(abstract: str, storm: bool = False) -> str:
    if not storm:
        translate_abstract_prompt = translate_template.invoke(
            {"type": "摘要", "content": abstract}
        )
        return deepseek_v3.invoke(translate_abstract_prompt).content
    return abstract


def download_arxiv_paper(
    arxiv_id: str, current_dir: str, storm: bool = False, index: Optional[int] = None
) -> str:
    try:
        title, abstract, link = get_information(arxiv_id)
    except:
        return "ID可能错误"
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_translatied_title = executor.submit(translate_title, title, storm)
        future_translated_abstract = executor.submit(
            translate_abstract, abstract, storm
        )
        future_parse = executor.submit(parse_arxiv, link.replace('abs', 'html'))
        translated_title = future_translatied_title.result()
        translated_abstract = future_translated_abstract.result()
        result = future_parse.result()
    title = f"STORMtemp{index}" if storm else title
    with open(f"{current_dir}/knowledgeBase/{title}.md", "w", encoding="utf-8") as f:
        if result is not None:
            f.write(result)
        else:
            f.write(abstract)
            return f"下载失败，请自行下载PDF并导入。\n\n标题：{translated_title}\n\n摘要：\n{translated_abstract}"
    return f"标题：{translated_title}\n\n摘要：\n{translated_abstract}"
