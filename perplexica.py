import requests
from modelclient import client1API_KEY, client1BASE_URL
proxies = {"http":"http://localhost:7890","https":"http://localhost:7890"}

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
    response = requests.post('http://127.0.0.1:3001/api/search', json=jsonquery, proxies=proxies)
    message = response.json()['message']
    sourcesList = response.json()['sources']
    referenceList = [
        f'[{i+1}] [{sourcesList[i]["metadata"]["title"]}]({sourcesList[i]["metadata"]["url"]})'
        for i in range(len(sourcesList))
    ]
    return message + '\n\n参考文献\n\n' + '\n\n'.join(referenceList)


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
    response = requests.post('http://127.0.0.1:3001/api/search', json=jsonquery, proxies=proxies)
    message = response.json()['message']
    sourcesList = response.json()['sources']
    referenceList = [
        f'[{i+1}] [{sourcesList[i]["metadata"]["title"]}]({sourcesList[i]["metadata"]["url"]})'
        for i in range(len(sourcesList))
    ]
    return ("查找" + query + "有关论文",
            message + '\n\n参考文献\n\n' + '\n\n'.join(referenceList))


def stormSearch(query):
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
    response = requests.post('http://127.0.0.1:3001/api/search', json=jsonquery, proxies=proxies)
    message1 = response.json()['message']
    sourcesList1 = response.json()['sources']
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
    response = requests.post('http://127.0.0.1:3001/api/search', json=jsonquery, proxies=proxies)
    message2 = response.json()['message']
    sourcesList2 = response.json()['sources']
    message = message1 + '\n\n' + message2
    sourcesList = sourcesList1 + sourcesList2
    return message, sourcesList

