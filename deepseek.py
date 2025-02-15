from modelclient import client1, client4
from sympy import *
from io import StringIO
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
    final_response = StringIO()
    for chunk in response:
        final_response.write(chunk.choices[0].delta.content or "")
        yield final_response.getvalue()
