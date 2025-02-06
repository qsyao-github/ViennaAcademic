from gradio_client import Client

client = Client("http://localhost:7861/")

def update():
    _ = client.predict(api_name="/update")


def qanything_fetch(query):
    result = client.predict(query=query, api_name="/get_response")
    return result
