from modelclient import client1, client3
from latex2sympy2_extended import latex2sympy, normalize_latex, NormalizationConfig
import regex
import requests
from sympy import *

config = NormalizationConfig(basic_latex=True,
                             units=True,
                             malformed_operators=True,
                             nits=True,
                             equations=False,
                             boxed=False)


def extract_formulas(text):
    # 使用正则表达式匹配 $ 或 $$ 包围的内容
    inline_formulas = regex.findall(r'\$(.*?)\$', text)
    block_formulas = regex.findall(r'\$\$(.*?)\$\$', text, regex.DOTALL)
    formulas = []
    # 返回所有匹配的公式，包括行内公式和块级公式
    for formula in (inline_formulas + block_formulas):
        if formula:
            if "=" not in formula:
                try:
                    formula = normalize_latex(formula, config)
                    expr = latex2sympy(formula)
                    try:
                        newExpr = expr.doit()
                    except:
                        newExpr = expr
                    newExpr = simplify(newExpr, rational=True, doit=True)
                    if formula != latex(newExpr):
                        latexExpr = latex(newExpr)
                        formulas.append("$" + formula + " = " + latexExpr +
                                        "$")
                except:
                    pass
    return formulas


def check_formulas(text):
    inline_formulas = regex.findall(r'\$(.*?)\$', text)
    block_formulas = regex.findall(r'\$\$(.*?)\$\$', text, regex.DOTALL)
    formulas = []
    for formula in (inline_formulas + block_formulas):
        components = formula.split("=")
        try:
            candidates = [
                latex2sympy(f"{components[i]}-({components[i+1]})")
                for i in range(len(components) - 1)
            ]
            checks = []
            for candidate in candidates:
                try:
                    newExpr = candidate.doit()
                    newExpr = simplify(newExpr, rational=True, doit=True)
                except:
                    newExpr = simplify(newExpr, rational=True, doit=True)
                checks.append(newExpr)
            for i in range(len(checks)):
                if latex(candidates[i]) != latex(checks[i]) and latex(
                        checks[i]) != '0':
                    formulas.append(
                        f"请用户检查以下等式：${components[i]} = {components[i+1]}$")
        except:
            pass
    return formulas


def attachHints(query, answer=""):
    formulas = extract_formulas(query)
    wrong_answer = check_formulas(answer) if answer else []
    if formulas:
        query += "\n提示：\n" + "\n".join(formulas)
    if wrong_answer:
        query += "\n" + "\n".join(wrong_answer)
    return query


def translate(query):
    translateMessage = [{
        "role":
        "system",
        "content":
        """你将看到一个理科题目，将其译为中文。如果其本来就是中文，不要改动。不要返回除了题目以外的其它信息"""
    }, {
        "role": "user",
        "content": query
    }]
    response = client1.chat.completions.create(model="gpt-4o-mini",
                                               messages=translateMessage)
    return response.choices[0].message.content


def deepseek(query):
    message = [{"role": "user", "content": query}]
    response = client3.chat.completions.create(model="deepseek-r1",
                                               messages=message,
                                               stream=True)
    for chunk in response:
        yield chunk.choices[0].delta.content or ""


def solve(query):
    query = translate(query).strip(";")
    query = attachHints(query, "")
    yield query
    response = deepseek(query)
    content = ""
    for chunk in response:
        content += chunk
        yield content
    index = content.find("[思考结束]")
    if index != -1:
        content = content[content.find("[思考结束]") + 6:]
        yield content
    checks = check_formulas(content)
    yield content + ("\n\n老卫提示：" + "\n\n" + "\n\n".join(
        checks) if checks else "")
