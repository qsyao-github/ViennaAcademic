from DrissionPage import Chromium

def ppsearch(query):
    browser = Chromium()  
    # 获取标签页对象
    tab = browser.latest_tab  
    # 创建页面对象，并启动或接管浏览器
    tab.get('http://localhost:3000')
    textbox=tab.ele('xpath:/html/body/div/main/div/div/div/div/div/form/div/textarea')
    search_btn=tab.ele('xpath:/html/body/div/main/div/div/div/div/div/form/div/div/div[2]/button')
    textbox.input(query)
    search_btn.click(by_js=None)
    tab.wait.eles_loaded('xpath:/html/body/div/main/div/div/div/div[2]/div[2]/div/div[1]/div[2]/div[5]/div[2]/div[1]/div[2]/p',timeout=60)
    answer=tab.ele('xpath:/html/body/div/main/div/div/div/div[2]/div[2]/div/div[1]/div[2]/div[2]')
    return answer.text
