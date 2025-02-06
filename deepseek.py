from modelclient import client1, client3
from latex2sympy2_extended import latex2sympy, normalize_latex, NormalizationConfig
import regex
from chat import formatFormula
from sympy import *
from Drission import get_wolfram

config = NormalizationConfig(basic_latex=True,
                             units=True,
                             malformed_operators=True,
                             nits=True,
                             equations=False,
                             boxed=False)


def extract_formulas(text):
    all_formulas = regex.findall(r'\$(.*?)\$', text) + regex.findall(
        r'\$\$(.*?)\$\$', text, regex.DOTALL)
    formulas = []
    for formula in all_formulas:
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
                    latexExpr = latex(newExpr)
                    if formula != latexExpr:
                        formulas.append(f"${formula} = {latexExpr}$")
                except:
                    pass
    return formulas


def check_formulas(text):
    all_formulas = regex.findall(r'\$(.*?)\$', text) + regex.findall(
        r'\$\$(.*?)\$\$', text, regex.DOTALL)
    formulas = []
    for formula in all_formulas:
        components = formula.split("=")
        try:
            candidates = [
                latex2sympy(f"{components[i]}-({components[i+1]})")
                for i in range(len(components) - 1)
            ]
            for i, candidate in enumerate(candidates):
                try:
                    newExpr = candidate.doit()
                except:
                    pass
                newExpr = simplify(newExpr, rational=True, doit=True)
                latex_check = latex(newExpr)
                if latex(candidate) != latex_check and latex_check != '0':
                    formulas.append(
                        f"请用户检查以下等式：${components[i]} = {components[i+1]}$")
        except:
            pass
    return formulas


def attachHints(query):
    hints = get_wolfram(query).strip()
    if hints:
        query = "Wolframalpha提示:\n```\n" + hints + "\n```\n" + query
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


def deepseek(query, messages = None):
    if messages is None:
        messages = [{"role": "user", "content": query}]
    messages = [{k: message[k] for k in ["role", "content"]} for message in messages]
    response = client1.chat.completions.create(
        model="deepseek-r1-distill-llama-70b", messages=messages, stream=True)
    for chunk in response:
        yield chunk.choices[0].delta.content or ""


def solve(query):
    response = deepseek(query)
    content = ""
    for chunk in response:
        content += chunk
        yield content
    # index = content.find("[思考结束]")
    index = content.find(r"</think>")
    if index != -1:
        # content = content[index + 6:]
        content = formatFormula(content[index + 8:])
        yield content
    yield content

