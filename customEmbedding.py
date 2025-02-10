from typing import List
from langchain_core.embeddings import Embeddings
from openai import OpenAI

client1API_KEY = "sk-IuSViVGW5Iwmdoip9594C084049342E3Bb40Af4899CdB08b"
client1BASE_URL = "https://api.kenxu.top:5/v1"
client1 = OpenAI(api_key=client1API_KEY, base_url=client1BASE_URL)

def groupLists(lst: List[str]):
    # 将lst中每32个元素分为1组，最后一组可能不足32个元素
    grouped = [lst[i:i + 32] for i in range(0, len(lst), 32)]
    return grouped


class CustomEmbeddings(Embeddings):

    def __init__(self, model: str):
        self.model = model

    def embed_query(self, text: str) -> List[float]:
        """Embed query text."""
        embedding = client1.embeddings.create(input=text, model=self.model)
        return embedding.data[0].embedding

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed search docs."""
        grouped = groupLists(texts)
        finalEmbedding = []
        for group in grouped:
            embedding = client1.embeddings.create(input=group,
                                                    model=self.model)
            finalEmbedding.extend(
                [vector.embedding for vector in embedding.data])
        return finalEmbedding
