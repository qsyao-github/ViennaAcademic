import os
from customEmbeddings import CustomEmbeddings, CustomCompressor
from langchain_community.vectorstores.faiss import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.retrievers import ContextualCompressionRetriever

embedding_model_name = 'netease-youdao/bce-embedding-base_v1'

embed_model = CustomEmbeddings(model=embedding_model_name)
reranker = CustomCompressor(10)

text_splitter = RecursiveCharacterTextSplitter(separators=[
    r"\n{2,}", r"\n+", r"\s{2,}", r"(?<=[.!?;])\s+|(?<=[。？！；])",
    r"(?<=[,])\s+|(?<=[，])", r"\s+"
],
                                               is_separator_regex=True,
                                               chunk_overlap=32,
                                               chunk_size=512)
check_chars = ['。', '！', '？', '.', '!', '?']


def get_document(file):
    documents = TextLoader(file).load()
    texts = text_splitter.split_documents(documents)
    return texts


def get_retriever(file):
    total_texts = get_document(file)
    if total_texts:
        retriever = FAISS.from_documents(
            total_texts,
            embed_model,
            distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT)
        return retriever


def save_retriever(file):
    try:
        retriever = get_retriever(f'knowledgeBase/{file}.md')
        if retriever is not None:
            retriever.save_local('retrievers', file)
    except:
        pass


def remove_retriever(file):
    try:
        os.remove(f'retrievers/{file}.pkl')
        os.remove(f'retrievers/{file}.faiss')
    except:
        pass


def update():
    knowledgeBase = set(
        os.path.splitext(file)[0] for file in os.listdir('knowledgeBase'))
    retrievers = set(
        os.path.splitext(file)[0] for file in os.listdir('retrievers'))
    for file in knowledgeBase - retrievers:
        save_retriever(file)
    for file in retrievers - knowledgeBase:
        remove_retriever(file)


def merge_retrievers():
    retrievers = [
        FAISS.load_local('retrievers',
                         embed_model,
                         file,
                         distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT,
                         allow_dangerous_deserialization=True)
        for file in set(
            os.path.splitext(file)[0] for file in os.listdir('retrievers'))
    ]
    base_retriever = retrievers.pop()
    for retriever in retrievers:
        base_retriever.merge_from(retriever)
    base_retriever = base_retriever.as_retriever(search_type="similarity",
                                                 search_kwargs={
                                                     "score_threshold": 0.35,
                                                     "k": 100,
                                                     "fetch-k": 100
                                                 })
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=reranker, base_retriever=base_retriever)
    return compression_retriever


def get_response(query):
    compression_retriever = merge_retrievers()
    response = compression_retriever.invoke(query)
    text_response = []
    for document in response:
        indicator = "Source: "
        content = document.page_content.strip(' \n')
        if content and '#' not in content and '\n' not in content and any(
                char in content for char in
                check_chars) and document.metadata["relevance_score"] >= 0.35:
            source = document.metadata["source"][14:]
            if source.startswith('STORMtemp'):
                source = source[9:]
                indicator = "Number: "
            source = os.path.splitext(source)[0]
            text_response.append(content + f' [{indicator}{source}]')
    return '\n\n'.join(text_response)
