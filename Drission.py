from DrissionPage import Chromium, ChromiumOptions

co = ChromiumOptions().headless(True)
co = co.set_argument('--no-sandbox')
browser = Chromium(co)
tab = browser.latest_tab

def get_html(url):
    tab.get(url, timeout=10)
    with open('temp.html', 'w') as f:
        f.write(tab.html)
