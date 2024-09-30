import requests


def webSearch(query):
    jsonquery = {
        "chatModel": {
            "provider":
            "custom_openai",
            "model":
            "gpt-4o-mini",
            "customOpenAIBaseURL":
            "https://api.kenxu.top:5/v1",
            "customOpenAIKey":
            "sk-xCBtJ7y0e9Eg7kAR895b5b7739A4490386E0E0Fc6c2a18C9"
        },
        "embeddingModel": {
            "provider": "ollama",
            "model": "mxbai-embed-large:latest"
        },
        "focusMode": "webSearch",
        "query": query
    }
    response = requests.post('http://115.45.12.77:3001/api/search',
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
            "https://api.kenxu.top:5/v1",
            "customOpenAIKey":
            "sk-xCBtJ7y0e9Eg7kAR895b5b7739A4490386E0E0Fc6c2a18C9"
        },
        "embeddingModel": {
            "provider": "ollama",
            "model": "mxbai-embed-large:latest"
        },
        "focusMode": "academicSearch",
        "query": query
    }
    response = requests.post('http://115.45.12.77:3001/api/search',
                             json=jsonquery)
    message = response.json()['message']
    sourcesList = response.json()['sources']
    referenceList = [
        f'[{source["metadata"]["title"]}]({source["metadata"]["url"]})'
        for source in sourcesList
    ]
    return message + '\n\n' + '\n\n'.join(referenceList)
