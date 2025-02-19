import requests
from modelclient import client1API_KEY, client1BASE_URL, client2API_KEY

proxies = {"http": "http://localhost:7890", "https": "http://localhost:7890"}


def constructQuery(query, focusMode):
    return {
        "chatModel": {
            "provider": "custom_openai",
            "model": "glm-4-flash",
            "customOpenAIBaseURL": 'https://open.bigmodel.cn/api/paas/v4',
            "customOpenAIKey": client2API_KEY
        },
        "embeddingModel": {
            "provider": "ollama",
            "model": "snowflake-arctic-embed2:latest"
        },
        "optimizationMode": "balanced",
        "focusMode": focusMode,
        "query": query
    }


def getResult(jsonquery):
    response = requests.post('http://127.0.0.1:3001/api/search',
                             json=jsonquery,
                             proxies=proxies)
    message = response.json()['message']
    sourcesList = response.json()['sources']
    referenceList = [
        f'[{i+1}] [{source["metadata"]["title"]}]({source["metadata"]["url"]})'
        for i, source in enumerate(sourcesList)
    ]
    return message, referenceList, sourcesList


def webSearch(query):
    try:
        jsonquery = constructQuery(query, "webSearch")
        message, referenceList, _ = getResult(jsonquery)
        return (f"请搜索{query}",
                message + '\n\n参考文献\n\n' + '\n\n'.join(referenceList))
    except:
        return (f"请搜索{query}", "老卫可能在深圳")


def academicSearch(query):
    try:
        jsonquery = constructQuery(query, "academicSearch")
        message, referenceList, _ = getResult(jsonquery)
        return ("查找" + query + "有关论文",
                message + '\n\n参考文献\n\n' + '\n\n'.join(referenceList))
    except:
        return ("查找" + query + "有关论文", "老卫可能在深圳")


def stormSearch(query):
    jsonquery = constructQuery(query, "academicSearch")
    message1, _, sourcesList1 = getResult(jsonquery)
    jsonquery = constructQuery(query, "webSearch")
    message2, _, sourcesList2 = getResult(jsonquery)
    message = message1 + '\n\n' + message2
    sourcesList = sourcesList1 + sourcesList2
    return message, sourcesList
