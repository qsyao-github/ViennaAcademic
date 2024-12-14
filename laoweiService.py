from gradio_client import Client, handle_file
from modelclient import client1


def generate(topic, max_conv_turn=3, max_perspective=3, search_top_k=3):
    if topic.strip() == "":
        return "Enter the topic"
    else:
        client = Client("http://127.0.0.1:7861/")
        result = client.predict(topic=topic,
                                max_conv_turn=max_conv_turn,
                                max_perspective=max_perspective,
                                search_top_k=search_top_k,
                                api_name="/generate")
        return result


def parseEverything(path):
    client = Client("http://127.0.0.1:7861/")
    result = client.predict(source=handle_file(path),
                            api_name="/parseEverything")
    return result


def downloadArxivPaper(arxiv_id):
    client = Client("http://127.0.0.1:7861/")
    title, abstract, content = client.predict(arxivID=arxiv_id,
                                              api_name="/downloadArxivPaper")
    with open(f'paper/{title.replace(" ", "_")}.md', 'w', encoding='utf-8') as f:
        f.write(content)
    return [{
        "text": f"下载arxiv:{arxiv_id}并翻译摘要",
        "files": []
    }, {
        "text": abstract,
        "files": []
    }]
