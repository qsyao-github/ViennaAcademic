from openai import OpenAI
import regex
from executeCode import execute_code
from perplexica import ppsearch
from omniparse import parseEverything

client=OpenAI(api_key="sk-xCBtJ7y0e9Eg7kAR895b5b7739A4490386E0E0Fc6c2a18C9",
              base_url="https://api.kenxu.top:5/v1")

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
def promptcall(message):
    return message
def historyParse(history):
    returnList=[]
    for ans in history:
        returnList+=[{'role': 'user', 'content': ans[0]}, {'role':'assistant','content': ans[1]}]
    return returnList
class chatBot:

    def __init__(self, history):
        self.chatHistory = [{
            'role':
            'system',
            'content':
            """对话过程中支持使用函数调用，由#、函数名、大括号内参数构成。#websearch{搜索关键词}调用搜索引擎。#python{完整代码，空行}执行代码"""
        }]+historyParse(history)

    def answer(self, query):
        if query is not None:
            query=toolcall(query)
            response=client.chat.completions.create(
    model="glm4",
    messages=self.chatHistory+[{"role":"user","content":query}]
)
            response = toolcall(response.choices[0].message.content)
            return response
        return "请输入内容"
