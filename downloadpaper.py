from modelclient import client1 as client
import urllib.request as libreq
import xml.etree.ElementTree as ET
from doclingParse import parseArxiv


def query(prompt):
    response = client.chat.completions.create(model="gpt-4o-mini",
                                              messages=[{
                                                  "role": "user",
                                                  "content": prompt
                                              }])
    return response.choices[0].message.content


def getInformation(arxivID):
    with libreq.urlopen(
            f'http://export.arxiv.org/api/query?id_list={arxivID}') as url:
        r = url.read().decode('utf-8')
    root = ET.fromstring(r)
    prefix = "{http://www.w3.org/2005/Atom}"
    entry = root.find(prefix + 'entry')
    return entry.find(prefix + 'title').text.replace(
        "\n", ""), entry.find(prefix + 'summary').text.replace(
            "\n",
            ""), entry.find(prefix + 'link').get('href').replace('abs', 'html')


def getTranslation(title, abstract):
    translated_title = query(f"将下列论文标题译为中文，不要返回除标题以外的其它内容：\n{title}")
    translated_abstract = query(f"将下列论文摘要译为中文，不要返回除摘要以外的其它内容：\n{abstract}")
    return translated_title, translated_abstract


def downloadArxivPaper(arxivID, storm=False, index=None):
    try:
        title, abstract, link = getInformation(arxivID)
    except:
        return "ID可能错误"
    if not storm:
        translated_title, translated_abstract = getTranslation(title, abstract)
    else:
        translated_title, translated_abstract = title, abstract
    title = title if not storm else f"STORMtemp{index}"
    result = parseArxiv(link)
    with open(f'knowledgeBase/{title}.md','w', encoding='utf-8') as f:
        if result is not None:
            f.write(result)
        else:
            f.write(abstract)
            return f"下载失败，请自行下载PDF并导入。\n\n标题：{translated_title}\n\n摘要：\n{translated_abstract}"
    return f"标题：{translated_title}\n\n摘要：\n{translated_abstract}"
