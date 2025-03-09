from searXNG import searxng_websearch


def attach_web_result(query: str) -> str:
    results = searxng_websearch(query)
    return f'{"\n\n".join(
        f"# {i}. {title}\n{snippet}"
        for i, (title, snippet, _) in enumerate(results, start=1)
    )}\n'
