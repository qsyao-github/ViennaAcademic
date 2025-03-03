import urllib.request as libreq
import xml.etree.ElementTree as ET
from docling_parser import parse_arxiv
from modelclient import gpt_4o_mini
from langchain_core.prompts import ChatPromptTemplate
from typing import Tuple, Optional

translate_template = ChatPromptTemplate.from_messages(
    [
        ("system", "请将下列论文{type}译为中文，不要返回除{type}以外的其它内容"),
        ("user", "{content}"),
    ]
)


def get_information(arxiv_id: str) -> Tuple[str, str, str]:
    with libreq.urlopen(f"http://export.arxiv.org/api/query?id_list={arxiv_id}") as url:
        r = url.read().decode("utf-8")
    root = ET.fromstring(r)
    prefix = "{http://www.w3.org/2005/Atom}"
    entry = root.find(prefix + "entry")
    return (
        entry.find(prefix + "title").text.replace("\n", ""),
        entry.find(prefix + "summary").text.replace("\n", ""),
        entry.find(prefix + "link").get("href").replace("abs", "html"),
    )


def get_translation(title: str, abstract: str) -> Tuple[str, str]:
    translate_title_prompt = translate_template.invoke(
        {"type": "标题", "content": title}
    )
    translate_abstract_prompt = translate_template.invoke(
        {"type": "摘要", "content": abstract}
    )
    translated_title = gpt_4o_mini.invoke(translate_title_prompt).content
    translated_abstract = gpt_4o_mini.invoke(translate_abstract_prompt).content
    return translated_title, translated_abstract


def download_arxiv_paper(
    arxiv_id: str, current_dir: str, storm: bool = False, index: Optional[int] = None
) -> str:
    try:
        title, abstract, link = get_information(arxiv_id)
    except:
        return "ID可能错误"
    if not storm:
        translated_title, translated_abstract = get_translation(title, abstract)
    else:
        translated_title, translated_abstract = title, abstract
    title = f"STORMtemp{index}" if storm else title
    result = parse_arxiv(link)
    with open(f"{current_dir}/knowledgeBase/{title}.md", "w", encoding="utf-8") as f:
        if result is not None:
            f.write(result)
        else:
            f.write(abstract)
            return f"下载失败，请自行下载PDF并导入。\n\n标题：{translated_title}\n\n摘要：\n{translated_abstract}"
    return f"标题：{translated_title}\n\n摘要：\n{translated_abstract}"
