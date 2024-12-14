import requests
from modelclient import client1API_KEY, client1BASE_URL


def webSearch(query):
    jsonquery = {
        "chatModel": {
            "provider": "custom_openai",
            "model": "gpt-4o-mini",
            "customOpenAIBaseURL": client1BASE_URL,
            "customOpenAIKey": client1API_KEY
        },
        "embeddingModel": {
            "provider": "ollama",
            "model": "mxbai-embed-large:latest"
        },
        "optimizationMode": "balanced",
        "focusMode": "webSearch",
        "query": query
    }
    response = requests.post('http://127.0.0.1:3001/api/search', json=jsonquery)
    message = response.json()['message']
    sourcesList = response.json()['sources']
    referenceList = [
        f'[{source["metadata"]["title"]}]({source["metadata"]["url"]})'
        for source in sourcesList
    ]
    return message + '\n\n' + '\n\n'.join(referenceList)


def academicSearch(query):
    jsonquery = {
        "chatModel": {
            "provider": "custom_openai",
            "model": "gpt-4o-mini",
            "customOpenAIBaseURL": client1BASE_URL,
            "customOpenAIKey": client1API_KEY
        },
        "embeddingModel": {
            "provider": "ollama",
            "model": "mxbai-embed-large:latest"
        },
        "optimizationMode": "balanced",
        "focusMode": "academicSearch",
        "query": query
    }
    response = requests.post('http://127.0.0.1:3001/api/search', json=jsonquery)
    message = response.json()['message']
    sourcesList = response.json()['sources']
    referenceList = [
        f'[{source["metadata"]["title"]}]({source["metadata"]["url"]})'
        for source in sourcesList
    ]
    return ("查找" + query + "有关论文",
            message + '\n\n' + '\n\n'.join(referenceList))
