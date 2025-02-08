from DrissionPage import Chromium, ChromiumOptions
import re
co = ChromiumOptions().headless(True)
co = co.set_argument('--no-sandbox')
browser = Chromium(co)
tab = browser.latest_tab

def isChinese(query):
    return bool(re.search(r'[\u4e00-\u9fff]', query))

def get_html(url):
    success = tab.get(url, timeout=10, retry=1)
    if success:
        with open('temp.html', 'w') as f:
            f.write(tab.html)
    return success


def get_wolfram(query):
    finalAnswer = []
    tab.get(f'https://www.wolframalpha.com/input?i={query}&lang=zh')
    try:
        answer_head = tab.ele('xpath:/html/body/div/div/main/main/div[2]/div/div[2]/section',timeout=10)
        answers = answer_head.eles("@|tag()=h2@|tag()=img")
        for answer in answers:
            if answer.tag == 'h2':
                temp = '# '+answer.ele('xpath:/span').text
            elif answer.tag == 'img':
                temp = answer.attr('alt')
            if temp and '图片' not in temp:
                finalAnswer.append(temp)
        return '\n'.join(finalAnswer)
    except:
        return ''

