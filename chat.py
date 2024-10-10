from openai import OpenAI
from zhipuai import ZhipuAI
import regex
from executeCode import execute_code
from perplexica import webSearch, academicSearch
from paper import readPaper, translatePapertoChinese, translatePapertoEnglish, polishPaper, attach

client1 = OpenAI(api_key="sk-114514",
                 base_url="https://1919810.com/v1")
client2 = ZhipuAI(api_key="ee45e4")


def python(code):
    return f"""\n```
{execute_code(code)}
```\n"""


def toolcall(message):
    functions = {'#websearch': webSearch, '#python': python}
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
        '#polishPaper': polishPaper,
        '#findPaper': academicSearch,
        '#websearch': webSearch
    }
    pattern = r'#(attach|readPaper|translatePapertoChinese|translatePapertoEnglish|polishPaper|findPaper|websearch)\{((?:[^{}]|(?:\{(?:[^{}]|(?R))*\}))*)\}'
    matches = regex.findall(pattern, message)
    for tag, param in matches:
        if tag == 'websearch':
            message = (f'请搜索{param}', webSearch(param))
        else:
            function_to_call = functions[f"#{tag}"]
            replacement = function_to_call(param)
            if type(replacement) == str:
                message = message.replace(f"#{tag}{{{param}}}", replacement)
            else:
                message = replacement
    return message


def historyParse(history):
    returnList = []
    for ans in history:
        returnList += [{
            'role': 'user',
            'content': ans[0].text
        }, {
            'role': 'assistant',
            'content': ans[1].text
        }]
    return returnList


class chatBot:

    def __init__(self, history):
        self.chatHistory = historyParse(history)

    def answer(self, query, token, nowTime):
        if query is not None:
            totalLength = len(query) + token
            # 生成当前时间的格式化字符串

            if totalLength < 8000:
                response = client1.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=self.chatHistory + [{
                        'role':
                        'system',
                        'content':
                        """你可使用魔术指令，它们形如#function{param}，大括号需紧跟函数名。若你需要上网搜索，请在回答中加入"#websearch{搜索内容}"；若你需要制作动画，请在回答中加入"#manim{你的代码}，文本请使用英文。若你需要运行Python代码，请在回答中加入"#python{代码}"。你可以使用numpy, scipy, sympy, matplotlib。请将绘制的图表保存至"""
                        + f"{nowTime}.png"
                    }] + [{
                        "role": "user",
                        "content": query
                    }])
            elif totalLength < 128000:
                response = client2.chat.completions.create(
                    model="glm-4-flash",
                    messages=self.chatHistory + [{
                        'role':
                        'system',
                        'content':
                        """你可使用魔术指令，它们形如#function{param}，大括号需紧跟函数名。若你需要上网搜索，请在回答中加入"#websearch{搜索内容}"；若你需要制作动画，请在回答中加入"#manim{你的代码}，文本请使用英文。若你需要运行Python代码，请在回答中加入"#python{代码}"。你可以使用numpy, scipy, sympy等第三方包。请将绘制的图表保存至"""
                        + f"{nowTime}.png"
                    }] + [{
                        "role": "user",
                        "content": query
                    }])
            else:
                print('using gemini')
                response = client1.chat.completions.create(
                    model="gemini-1.5-flash",
                    messages=self.chatHistory + [{
                        'role':
                        'system',
                        'content':
                        """你可使用魔术指令，它们形如#function{param}，大括号需紧跟函数名。若你需要上网搜索，请在回答中加入"#websearch{搜索内容}"；若你需要制作动画，请在回答中加入"#manim{你的代码}，，文本请使用英文。若你需要运行Python代码，请在回答中加入"#python{代码}"。你可以使用numpy, scipy, sympy等第三方包。请将绘制的图表保存至"""
                        + f"{nowTime}.png"
                    }] + [{
                        "role": "user",
                        "content": query
                    }])
            response = toolcall(response.choices[0].message.content)
            print(response)
            return response
        return "请输入内容"
