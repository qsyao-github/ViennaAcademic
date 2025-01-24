"""
pip install -U pydantic
pip install langchain==0.1.0 langchain-community==0.0.9 langchain-core==0.1.7 langsmith==0.0.77 simsimd
"""
import os
from BCEmbedding.tools.langchain import BCERerank
from langchain_community.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain.retrievers import ContextualCompressionRetriever
from langchain.text_splitter import RecursiveCharacterTextSplitter
# init embedding model
embedding_model_name = 'maidalun1020/bce-embedding-base_v1'
embedding_model_kwargs = {'device': 'cuda:0'}
embedding_encode_kwargs = {
    'batch_size': 100,
    'normalize_embeddings': True,
    'show_progress_bar': False
}

embed_model = HuggingFaceEmbeddings(model_name=embedding_model_name,
                                    encode_kwargs=embedding_encode_kwargs)

reranker_args = {'model': 'maidalun1020/bce-reranker-base_v1', 'top_n': 10}
reranker = BCERerank(**reranker_args)

def get_document(file):
    documents = TextLoader(file).load()
    text_splitter = RecursiveCharacterTextSplitter(separators = [r"\n+#{1,6}\s+","\n{2,}"], is_separator_regex=True, chunk_overlap=20, chunk_size=100)
    texts = text_splitter.split_documents(documents)
    return texts


def get_retriever(file):
    print(file)
    total_texts = get_document(file)
    retriever = FAISS.from_documents(
        total_texts,
        embed_model,
        distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT)
    return retriever
    

def update():
    knowledgeBase = set([os.path.splitext(file)[0] for file in os.listdir('knowledgeBase')])
    retrievers = set([os.path.splitext(file)[0] for file in os.listdir('retrievers')])
    for file in knowledgeBase-retrievers:
        retriever = get_retriever(f'knowledgeBase/{file}.md')
        retriever.save_local('retrievers', file)
        print(f'{file} retriever saved')
    for file in retrievers-knowledgeBase:
        try:
            os.remove(f'retrievers/{file}.pkl')
            os.remove(f'retrievers/{file}.fiass')
            print(f'{file} retriever removed')
        except:
            print('Admins please check for the file')


def merge_retrievers():
    retrievers = [FAISS.load_local('retrievers', embed_model, file, distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT) for file in set([os.path.splitext(file)[0] for file in os.listdir('retrievers')])]
    print('retrievers ready')
    base_retriever = retrievers.pop()
    for retriever in retrievers:
        base_retriever.merge_from(retriever)
    base_retriever = base_retriever.as_retriever(
            search_type="similarity",
            search_kwargs={
                "score_threshold": 0.35,
                "k": 10
            })
    print('merged')
    compression_retriever = ContextualCompressionRetriever(
        base_compressor=reranker, base_retriever=base_retriever)
    return compression_retriever


def get_response(query):
    compression_retriever = merge_retrievers()
    response = compression_retriever.get_relevant_documents(query)
    return response


import time
start = time.time()
result = get_response("什么是注意力机制")
with open('test.md', 'w') as f:
    for i, document in enumerate(result):
        print(f'No. {i+1}，相似度{document.metadata["relevance_score"]}')
        print(document.page_content)
        f.write(f'No. {i+1}，相似度{document.metadata["relevance_score"]}\n')
        f.write(document.page_content+'\n')
print(time.time()-start)
