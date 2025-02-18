from modelclient import client1, client4
from Drission import get_wolfram

def attachHints(query):
    hints = get_wolfram(query).strip()
    if hints:
        query = "Wolframalpha提示:\n```\n" + hints + "\n```\n" + query
    return query


def deepseek(messages):
    
    messages = [{k: message[k] for k in ["role", "content"]} for message in messages]
    response = client1.chat.completions.create(
        model="deepseek-r1-distill-llama-70b", messages=messages, temperature=0.6, stream=True)
    for chunk in response:
        yield chunk.choices[0].delta.content or ""
