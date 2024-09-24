import ollama
import regex
from ipython import execute_code
from perplexica import ppsearch
from omniparse import parseEverything


def websearch(query):
    return f'''\n```
{ppsearch(query)}
```\n'''


def python(code):
    return f"""\n```python
{code}
```
```
{execute_code(code)}
```\n"""


def attach(file):
    return f"""\n```
{parseEverything(file)}
```\n"""


def toolcall(message):
    functions = {'#websearch': websearch, '#python': python, '#attach': attach}
    pattern = r'#(websearch|python|attach)\{((?:[^{}]|(?:\{(?:[^{}]|(?R))*\}))*)\}'
    matches = regex.findall(pattern, message)
    for tag, param in matches:
        function_to_call = functions[f"#{tag}"]
        replacement = function_to_call(param)
        message = message.replace(f"#{tag}{{{param}}}", replacement)
    return message


class chatbot:

    def __init__(self):
        self.chatHistory = [{
            'role':
            'system',
            'content':
            """你可能需要上网搜索或执行python代码，请调用函数。函数由井号、函数名和大括号内的参数组成：#websearch{search_query}使用搜索引擎；#python{your_code}执行python代码"""
        }]

    def answer(self, query=None):
        if query is not None:
            self.chatHistory.append({'role': 'user', 'content': query})
            message = ""
            stream = ollama.chat(model='glm4',
                                 messages=self.chatHistory,
                                 stream=True)
            for chunk in stream:
                print(chunk['message']['content'], end='', flush=True)
                message += chunk['message']['content']
            message = toolcall(message)
            self.chatHistory.append({'role': 'assistant', 'content': message})
            return message
        return "请输入内容"


def chat():
    bot = chatbot()
    while True:
        query = input("用户：")
        if query == "exit":
            break
        else:
            print(bot.answer(query))
