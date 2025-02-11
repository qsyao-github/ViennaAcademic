import regex
from executeCode import execute_code, manim_render
from perplexica import webSearch, academicSearch
from paper import readPaper, translatePapertoChinese, translatePapertoEnglish, polishPaper, attach
from imageUtils import get_total_pixels, encode_image
from codeAnalysis import generate_docstring, optimize_code
from modelclient import client1, client2, qvqClient
import os


def python(code):
    return f"""\n
{execute_code(code)}
\n"""


def remove_newlines_from_formulas(text):
    # 用正则表达式匹配并替换
    return regex.sub(r'\$\$[\s\r\n]*(.*?)\s*[\s\r\n]*\$\$',
                     r'$$\1$$',
                     text,
                     flags=regex.DOTALL)


FIND_MAGIC_COMMAND_SUFFIX = r"\{((?:[^{}]|(?:\{(?:[^{}]|(?R))*\}))*)\}"


def toolcall(message, nowTime):
    functions = {
        'websearch': webSearch,
        'python': python,
        'manim': manim_render
    }
    pattern = r"<(\w+)>(.*?)</\1>"
    matches = regex.findall(pattern, message, regex.DOTALL)
    for tag, param in matches:
        if tag == 'manim':
            message = manim_render(param, nowTime)
        elif param.strip() != '':
            function_to_call = functions.get(tag, None)
            if function_to_call is not None:
                replacement = function_to_call(param.strip())
                message = message.replace(f"<{tag}>{param}</{tag}>",
                                          replacement)
    return message


def promptcall(message):
    functions = {
        '#attach': attach,
        '#findPaper': academicSearch,
        '#websearch': webSearch,
        '#generateDocstring': generate_docstring,
        '#optimizeCode': optimize_code
    }
    pattern = r'#(attach|findPaper|websearch|generateDocstring|optimizeCode)' + FIND_MAGIC_COMMAND_SUFFIX
    matches = regex.findall(pattern, message)
    for tag, param in matches:
        function_to_call = functions[f"#{tag}"]
        replacement = function_to_call(param)
        if isinstance(replacement, str):
            message = message.replace(f"#{tag}{{{param}}}", replacement)
        else:
            message = replacement
    return message


def modelInference(model, nowTime, query, chatbot, client):
    stream = client.chat.completions.create(
        model=model,
        messages=chatbot.chatHistory + [{
            'role':
            'system',
            'content':
            """你是强大的LLM Agent，你可以通过魔术命令上网、制作动画、执行Python代码。命令形如<function_name>params</function_name>。若你需要上网搜索，请在回答中加入"<websearch>关键字</websearch>"；若你需要使用manim制作动画，请在回答中加入"<manim>代码</manim>"。若你需要运行Python代码，请在回答中加入"<python>代码</python>"。你可以使用numpy, scipy, sympy, matplotlib。请将绘制的图表保存至"""
            + f"{nowTime}.png"
        }] + [{
            "role": "user",
            "content": query[0]["content"]
        }],
        stream=True)
    for chunk in stream:
        yield chunk.choices[0].delta.content or ""


def multimodelInference(model, query, chatbot):
    stream = client1.chat.completions.create(model=model,
                                             messages=chatbot.chatHistory +
                                             query,
                                             stream=True)
    for chunk in stream:
        yield chunk.choices[0].delta.content or ""


def insertHistory(text1, text2=None):
    if text2 is None:
        return {'role': 'user', 'content': text1}
    else:
        return [{
            'role': 'user',
            'content': text1
        }, {
            'role': 'assistant',
            'content': text2
        }]


def insertMultimodalHistory(text, encodedString):
    return {
        'role':
        'user',
        'content': [{
            "type": "text",
            "text": text
        }, {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{encodedString}"
            }
        }]
    }


def historyParse(history, multimodal=False):
    returnList = []
    sizeMax = 0
    if not multimodal:
        for ans in history:
            returnList.extend(insertHistory(ans[0].text, ans[1].text))
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
                        sizeMax = max(sizeMax, size)
                        txtFilePath = os.path.splitext(file)[0] + '.txt'
                        if os.path.exists(txtFilePath):
                            with open(txtFilePath, 'r') as f:
                                encodedString = f.read()
                        else:
                            encodedString = encode_image(file)
                            with open(txtFilePath, 'w') as f:
                                f.write(encodedString)
                        returnList.append(
                            insertMultimodalHistory(dialogue.text,
                                                    encodedString))
                else:
                    returnList.append({
                        'role': 'user',
                        'content': dialogue.text
                    })
    return returnList, sizeMax


def queryParse(query, multimodal=False):
    returnList = []
    if query:
        if not multimodal:
            returnList.append(insertHistory(query["text"]))
            size = 0
        else:
            image_pattern = regex.compile(r'.*\.(png|jpg|jpeg|tiff|bmp|heic)$',
                                          regex.IGNORECASE)
            files = query["files"]
            if files:
                file = files[0]["file"].path
                if image_pattern.match(file):
                    # size = get_total_pixels(file)
                    encodedString = encode_image(file)
                    txtFilePath = os.path.splitext(file)[0] + '.txt'
                    with open(txtFilePath, 'w') as f:
                        f.write(encodedString)
                    returnList.append(
                        insertMultimodalHistory(query["text"], encodedString))
            else:
                returnList.append(insertHistory(query["text"]))
                size = 0
        return returnList, 0


def formatFormula(string):
    return string.replace('\\(',
                          '$').replace('\\)',
                                       '$').replace('\\[',
                                                    '$$').replace('\\]', '$$')


class chatBot:

    def __init__(self, history, multimodal=False):
        self.chatHistory, self.size = historyParse(history, multimodal)

    def answer(self, query, nowTime, multimodal=False):
        query, _ = queryParse(query, multimodal)
        if not multimodal:
            if query is not None:
                try:
                    returnMessage = modelInference("gpt-4o-mini", nowTime, query,
                                                self, client1)
                
                    for chunk in returnMessage:
                        yield chunk
                except:
                    returnMessage = modelInference("glm-4-flash", nowTime, query, self, client2)
                    for chunk in returnMessage:
                        yield chunk
        else:
            if query is not None:
                for chunk in multimodelInference("pixtral-large-latest", query,
                                                 self):
                    yield chunk


class QvQchatBot(chatBot):

    def __init__(self, history):
        super().__init__(history, True)

    def answer(self, query):
        query, _ = queryParse(query, True)
        if query is not None:
            for chunk in qvqClient(self.chatHistory + query):
                yield chunk
