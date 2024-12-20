import regex
from executeCode import execute_code, manim_render
from perplexica import webSearch, academicSearch
from paper import readPaper, translatePapertoChinese, translatePapertoEnglish, polishPaper, attach
from imageUtils import get_total_pixels, encode_image
from modelclient import client1, client2
import os

def python(code):
    return f"""\n```
{execute_code(code)}
```\n"""


def toolcall(message, nowTime):
    functions = {
        '#websearch': webSearch,
        '#python': python,
        '#manim': manim_render
    }
    pattern = r'#(websearch|python|manim)\{((?:[^{}]|(?:\{(?:[^{}]|(?R))*\}))*)\}'
    matches = regex.findall(pattern, message)
    for tag, param in matches:
        if tag == 'manim':
            message = manim_render(param, nowTime)
        elif param.strip() != '':
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


def historyParse(history, multimodal=False):
    returnList = []
    sizeList = [0]
    if not multimodal:
        for ans in history:
            returnList += [{
                'role': 'user',
                'content': ans[0].text
            }, {
                'role': 'assistant',
                'content': ans[1].text
            }]
    else:
        image_pattern = regex.compile(r'.*\.(png|jpg|jpeg|tiff|bmp|heic)$',
                                      regex.IGNORECASE)
        for ans in history:
            for dialogue in ans:
                files = dialogue.files
                if files:
                    file = files[0].file.path
                    if image_pattern.match(file):
                        size = get_total_pixels(file)
                        sizeList[0] = max(sizeList[0], size)
                        if file[:file.rfind('.')] + '.txt' in os.listdir():
                            with open(file[:file.rfind('.')] + '.txt') as f:
                                encodedString = f.read()
                                returnList += [{
                                    'role':
                                    'user',
                                    'content': [{
                                        "type": "text",
                                        "text": dialogue.text
                                    }, {
                                        "type": "image_url",
                                        "image_url": {
                                            "url":
                                            f"data:image/png;base64,{encodedString}"
                                        }
                                    }]
                                }]
                        else:
                            encodedString = encode_image(file)
                            with open(file[:file.rfind('.')] + '.txt',
                                      'w') as f:
                                f.write(encodedString)
                            returnList += [{
                                'role':
                                'user',
                                'content': [{
                                    "type": "text",
                                    "text": dialogue.text
                                }, {
                                    "type": "image_url",
                                    "image_url": {
                                        "url":
                                        f"data:image/png;base64,{encodedString}"
                                    }
                                }]
                            }]
                else:
                    returnList += [{'role': 'user', 'content': dialogue.text}]
    return returnList, sizeList[0]


def queryParse(query, multimodal=False):
    if query:
        if not multimodal:
            returnList = [{'role': 'user', 'content': query["text"]}]
            size = 0
        else:
            image_pattern = regex.compile(r'.*\.(png|jpg|jpeg|tiff|bmp|heic)$',
                                          regex.IGNORECASE)
            files = query["files"]
            if files:
                file = files[0]["file"].path
                if image_pattern.match(file):
                    size = get_total_pixels(file)
                    encodedString = encode_image(file)
                    with open(file[:file.rfind('.')] + '.txt', 'w') as f:
                        f.write(encodedString)
                    returnList = [{
                        'role':
                        'user',
                        'content': [{
                            "type": "text",
                            "text": query["text"]
                        }, {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{encodedString}"
                            }
                        }]
                    }]
            else:
                returnList = [{'role': 'user', 'content': query["text"]}]
                size = 0
        return returnList, size


class chatBot:

    def __init__(self, history, multimodal=False):
        self.chatHistory, self.size = historyParse(history, multimodal)

    def answer(self, query, token, nowTime, multimodal=False):
        query, size = queryParse(query, multimodal)
        if not multimodal:
            if query is not None:
                totalLength = len(query[0]['content']) + token
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
                            "content": query[0]["content"]
                        }])
                else:
                    response = client2.chat.completions.create(
                        model="glm-4-flash",
                        messages=self.chatHistory + [{
                            'role':
                            'system',
                            'content':
                            """你可使用魔术指令，它们形如#function{param}，大括号需紧跟函数名。若你需要上网搜索，请在回答中加入"#websearch{搜索内容}"；若你需要制作动画，请在回答中加入"#manim{你的代码}，，文本请使用英文。若你需要运行Python代码，请在回答中加入"#python{代码}"。你可以使用numpy, scipy, sympy等第三方包。请将绘制的图表保存至"""
                            + f"{nowTime}.png"
                        }] + [{
                            "role": "user",
                            "content": query[0]["content"]
                        }])
                response = toolcall(response.choices[0].message.content,
                                    nowTime)
                return response
            return "请输入内容"
        else:
            if query is not None:
                content = query[0]['content']
                contentLength = len(content) if type(content) == str else len(
                    content[0]['text'])
                totalLength = contentLength + token
                pixelLength = max(self.size, size)
                try:
                    response = client1.chat.completions.create(
                        model="pixtral-large-latest",
                        messages=self.chatHistory + query)
                    response = response.choices[0].message.content
                except:
                    if totalLength < 8000 and pixelLength < 1806336:
                        response = client1.chat.completions.create(
                            model="minicpm-v",
                            messages=self.chatHistory + query)
                        response = response.choices[0].message.content
                    else:
                        response = "牢卫：图片过大或聊天过长，请清空历史记录后重试，尽量裁剪图片"
                return response
