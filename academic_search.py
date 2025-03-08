# arxiv
from langchain_community.retrievers import ArxivRetriever
retriever = ArxivRetriever()
def search_arxiv(query: str):
    docs = retriever.invoke(query)
    return [(doc.metadata['Title'], doc.page_content.replace('\n', ' '), doc.metadata['Entry ID']) for doc in docs]
# crossref
from habanero import Crossref
cr = Crossref()
def search_crossref(query: str):
    x = cr.works(query = query)
    return [(item["title"], item["abstract"], item["URL"]) for item in x['message']['items']]
