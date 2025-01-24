from gradio_client import Client


def update():
    client = Client("http://localhost:7862/")
    result = client.predict(
            api_name="/update"
    )


def qanything_fetch(query):
    client = Client("http://localhost:7862/")
    result = client.predict(
            query=query,
            api_name="/get_response"
    )
    return result


print(qanything_fetch("SSL算法如何从大量未标记数据中学习有判别力的特征？"))
