import requests


def webSearch(query):
    jsonquery = {
        "chatModel": {
            "provider":
            "custom_openai",
            "model":
            "gpt-4o-mini",
            "customOpenAIBaseURL":
            "https://114514.com/v1",
            "customOpenAIKey":
            "114514"
        },
        "embeddingModel": {
            "provider": "ollama",
            "model": "mxbai-embed-large:latest"
        },
        "focusMode": "webSearch",
        "query": query
    }
    response = requests.post('http://114514:3001/api/search',
                             json=jsonquery)
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
            "provider":
            "custom_openai",
            "model":
            "gpt-4o-mini",
            "customOpenAIBaseURL":
            "https://114514.com/v1",
            "customOpenAIKey":
            "114514"
        },
        "embeddingModel": {
            "provider": "ollama",
            "model": "mxbai-embed-large:latest"
        },
        "focusMode": "academicSearch",
        "query": query
    }
    response = requests.post('http://114514:3001/api/search',
                             json=jsonquery)
    message = response.json()['message']
    sourcesList = response.json()['sources']
    referenceList = [
        f'[{source["metadata"]["title"]}]({source["metadata"]["url"]})'
        for source in sourcesList
    ]
    return ("查找" + query + "有关论文",
            message + '\n\n' + '\n\n'.join(referenceList))
