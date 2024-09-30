from openai import OpenAI
import regex
from executeCode import execute_code
from perplexica import webSearch, academicSearch
from omniparse import parseEverything
from paper import readPaper, translatePapertoChinese, translatePapertoEnglish, polishPaper

client = OpenAI(api_key="sk-1145141919810",
                base_url="https://114514.com/v1")


def websearch(query):
    return f'''\n```
{webSearch(query)}
```\n'''


def academicsearch(query):
    return f'''\n```
{academicSearch(query)}
```\n'''


def python(code):
    return f"""\n```
{execute_code(code)}
```\n"""


def attach(file):
    return f"""\n```
{parseEverything(file)}
```\n"""


def toolcall(message):
    functions = {'#websearch': websearch, '#python': python}
    pattern = r'#(websearch|python)\{((?:[^{}]|(?:\{(?:[^{}]|(?R))*\}))*)\}'
    matches = regex.findall(pattern, message)
    for tag, param in matches:
        if param.strip() != '':
            function_to_call = functions[f"#{tag}"]
            replacement = function_to_call(param)
            message = message.replace(f"#{tag}{{{param}}}", replacement)
    return message


def promptcall(message):
    functions = {
        '#attach': attach,
        '#readPaper': readPaper,
        '#translatePapertoChinese': translatePapertoChinese,
        '#translatePapertoEnglish': translatePapertoEnglish,
        '#polishPaper': polishPaper
    }
    pattern = r'#(attach|readPaper|translatePapertoChinese|translatePapertoEnglish|polishPaper)\{((?:[^{}]|(?:\{(?:[^{}]|(?R))*\}))*)\}'
    matches = regex.findall(pattern, message)
    for tag, param in matches:
        function_to_call = functions[f"#{tag}"]
        replacement = function_to_call(param)
        message = message.replace(f"#{tag}{{{param}}}", replacement)
    return message


def historyParse(history):
    returnList = []
    for ans in history:
        returnList += [{
            'role': 'user',
            'content': ans[0]
        }, {
            'role': 'assistant',
            'content': ans[1]
        }]
    return returnList


class chatBot:

    def __init__(self, history):
        self.chatHistory = historyParse(history)

    def answer(self, query):
        if query is not None:
            query = promptcall(query)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=self.chatHistory + [{
                    'role':
                    'system',
                    'content':
                    """你可使用魔术指令，它们形如#function{param}，大括号需紧跟函数名。若你需要上网搜索，请在回答中加入"#websearch{搜索内容}"；若你需要运行Python代码，请在回答中加入"#python{代码}"。注意，若要获得标准输出，必须使用print，你可以使用numpy, scipy, sympy等第三方包"""
                }] + [{
                    "role": "user",
                    "content": query
                }])
            response = toolcall(response.choices[0].message.content)
            return response
        return "请输入内容"
