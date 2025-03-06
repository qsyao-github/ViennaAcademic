from drission import get_wolfram


def attach_hints(query: str) -> str:
    hints = get_wolfram(query).strip()
    if hints:
        query = f"Wolframalpha提示：\n```\n{hints}\n```\n{query}"
    return query
