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


def test_upload_image():
    path = "test.png"
    with open(path, "rb") as f:
        response = client.post(
            "/upload/image/123",
            files={"file": (path, f)},
        )

    print(response.json())


def test_upload_document():
    path = "test.pdf"
    with open(path, "rb") as f:
        response = client.post(
            "/upload/document/laowei/paper",
            files={"file": (path, f)},
        )
    print(response.json())


def test_media_files():
    # Test accessing a file in the media directory
    response = client.get("/media/123_test.png")
    with open("retest.png", "wb") as f:
        f.write(response.content)


def test_documents_files():
    # Test accessing a file in the documents directory
    response = client.get("/documents/laowei/paper/test.xml")
    with open("retest.xml", "wb") as f:
        f.write(response.content)


def test_list_files():
    response = client.get(
        "/list_files", params={"user": "laowei", "directory": "paper"}
    )
    print(response.json())
