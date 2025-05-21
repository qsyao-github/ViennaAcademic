from fastapi.testclient import TestClient
from fastapi_endpoint import app

client = TestClient(app)


def test_respond():
    response = client.post(
        "/respond",
        params={
            "query": "你好",
            "thread_id": "1",
            "chat_mode": "常规",
            "current_user": "laowei",
        },
    )
    for chunk in response.iter_text():
        print(chunk, end="\n")


test_respond()
