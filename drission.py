from DrissionPage import Chromium, ChromiumOptions

co = ChromiumOptions().headless(True)
co = co.set_argument("--no-sandbox")
browser = Chromium(co)
tab = browser.latest_tab


def get_wolfram(query: str) -> str:
    finalAnswer = []
    if not query or "\n" in query:
        return ""
    try:
        tab.get(f"https://www.wolframalpha.com/input?i={query}&lang=zh")
        answer_head = tab.ele(
            "xpath:/html/body/div/div/main/main/div[2]/div/div[2]/section", timeout=10
        )
        answers = answer_head.eles("@|tag()=h2@|tag()=img")
        for answer in answers:
            if answer.tag == "h2":
                temp = "# " + answer.ele("xpath:/span").text
            elif answer.tag == "img":
                temp = answer.attr("alt")
            if temp and "图片" not in temp and "图形" not in temp:
                finalAnswer.append(temp)
        return "\n".join(finalAnswer)
    except:
        return ""
