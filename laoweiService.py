from gradio_client import Client, handle_file

def generate(topic,max_conv_turn=3,max_perspective=3,search_top_k=3):
    if topic.strip() == "":
        return "Enter the topic"
    else:
        client = Client("http://192.168.1.250:7860/")
        result = client.predict(
                topic=topic,
                max_conv_turn=max_conv_turn,
                max_perspective=max_perspective,
                search_top_k=search_top_k,
                api_name="/generate"
        )
        return result
def solve(question):
    client = Client("http://192.168.1.250:7860/")
    result = client.predict(
            question=question,
            api_name="/solve"
    )
    return result
def parseEverything(path):
    client = Client("http://192.168.1.250:7860/")
    result = client.predict(
            source=handle_file(path),
            api_name="/parseEverything"
    )
    return result
