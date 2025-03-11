from searXNG import searxng_websearch
from academic_search import select_best_results
from typing import List, Tuple, Generator
from langchain_core.prompts import ChatPromptTemplate
from system_prompt import ACADEMIC_SEARCH
from modelclient import deepseek_v3
from io import StringIO

generate_summary_prompt_tempate = ChatPromptTemplate.from_messages(
    [
        ("system", ACADEMIC_SEARCH),
        ("user", "{content}"),
    ]
)


def attach_web_result(query: str) -> str:
    results = searxng_websearch(query)
    return f'{"\n\n".join(
        f"# {i}. {title}\n{snippet}"
        for i, (title, snippet, _) in enumerate(results, start=1)
    )}'


def attach_academic_result(query: str) -> str:
    results = select_best_results(query)
    return f'{"\n\n".join(
        f"# {i}. {title}\n{snippet}"
        for i, (title, snippet, _) in enumerate(results, start=1)
    )}\n\n{"\n\n".join(f"[{i}] [{title}]({link})" for i, (title, _, link) in enumerate(results, start=1))}'


def generate_summary(query: str) -> Generator[str, None, None]:
    best_results = attach_academic_result(query)
    prompt = generate_summary_prompt_tempate.invoke({"content": f"{best_results}\n{query}"})
    final_response = StringIO()
    final_response.write(f'{best_results}\n\n---\n\n')
    yield final_response.getvalue()
    response = deepseek_v3.stream(prompt)
    for chunk in response:
        final_response.write(chunk.content)
        yield final_response.getvalue()
