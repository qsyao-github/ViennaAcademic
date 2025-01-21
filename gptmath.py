from modelclient import client1, client2
import regex as re
import subprocess
import time


def remove_newlines_from_formulas(text):
    # 用正则表达式匹配并替换
    pattern = r'\$\$[\s\r\n]*(.*?)\s*[\s\r\n]*\$\$'
    replacement = r'$$\1$$'
    result = re.sub(pattern, replacement, text, flags=re.DOTALL)
    return result


def execute_code_math(code):
    # 将code写入temp.py中，用subprocess运行，返回文本形式结果
    with open('temp.py', 'w', encoding='utf-8') as f:
        f.write(code)

    process = subprocess.Popen(['python', 'temp.py'],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               text=True)
    start_time = time.time()

    # 等待进程结束或超时
    while True:
        if process.poll() is not None:  # 进程已经结束
            break
        if time.time() - start_time > 10:  # 超过时间限制
            process.terminate()  # 终止进程
            return "Verification time out, return #submit directly"
        time.sleep(0.1)  # 避免过于频繁的检查

    stdout, stderr = process.communicate()
    return stdout if stdout else '' + stderr if stderr else ''


def qwenmath(question):
    stream = client1.chat.completions.create(
        model="qwq-32b-preview",
        messages=[{
            "role":
            "system",
            "content":
            "You are a helpful and harmless assistant. You are Qwen developed by Alibaba. You should think step-by-step."
        }, {
            "role": "user",
            "content": question
        }],
        stream=True)
    for chunk in stream:
        yield chunk.choices[0].delta.content or ""


def gptChat(message):
    response = client1.chat.completions.create(model="gpt-4o-mini",
                                               messages=message)
    return response.choices[0].message.content


def claudeChat(message):
    response = client1.chat.completions.create(model="mistral-large-latest",
                                               messages=message)
    return response.choices[0].message.content


def glmChat(message):
    response = client2.chat.completions.create(model="glm-4-flash",messages=message)
    return response.choices[0].message.content


def pythonCall(answer):
    # 去掉原本存在的```output块
    answer = re.sub(r'```output\n(.*?)```', '', answer, flags=re.DOTALL)
    # 执行结果替换
    pattern = r'```python(.*?)```'

    def repl(match):
        code = match.group(1).strip()
        result = '```python\n' + code + '```\n' + '```output\n' + execute_code_math(
            code) + '```'  # 执行代码并获取结果
        return result  # 用执行结果替换代码

    # 执行替换
    replaced_text = re.sub(pattern, repl, answer, flags=re.DOTALL)
    return replaced_text


def solve(question):
    # translation
    translateMessage = [{
        "role":
        "system",
        "content":
        """You'll be given problem. Translated into English. If its already in English, leave it unchanged. Return the translated or unchanged problem only."""
    }, {
        "role": "user",
        "content": question
    }]
    question = gptChat(translateMessage)
    # qwen inference
    answer = ""
    stream = qwenmath(question)
    for chunk in stream:
        answer += chunk
        yield answer
    # rewrite
    rewriteMessage = [{
        "role":
        "system",
        "content":
        """You'll be given a question and a thought process. You're taking an exam. Rephrase the thought process given rigorously in markdown, only include necessary reasoning/calculation that contributes to the rigorousness of the thought process, wrap the final answer in \\boxed{}, and return nothing else."""
    }, {
        "role":
        "user",
        "content":
        'Question:\n' + question + "\nAnswer:\n" + answer
    }]
    answer = claudeChat(rewriteMessage)
    if answer.endswith('```') and answer.startswith('```markdown'):
        answer = answer[13:-3]
    answer = answer.replace(
        '\\(', '$').replace('\\)', '$').replace('\\[',
                                                '$$').replace('\\]', '$$')
    answer = remove_newlines_from_formulas(answer)
    translateMessage = [{
        "role": "user",
        "content": "我会提供一个问题的解题过程及答案，将其译为中文\n"+answer
    }]
    answerChi = glmChat(translateMessage)
    answerChi = answerChi.replace(
        '\\(', '$').replace('\\)', '$').replace('\\[',
                                                '$$').replace('\\]', '$$')
    answerChi = remove_newlines_from_formulas(answerChi)
    finalAnswer = (answerChi + '\n\n' + answer)
    yield finalAnswer
