import re
from DrissionPage import Chromium


def parseDocument(file_path):
    browser=Chromium()
    tab=browser.latest_tab
    tab.get('http://localhost:8000')
    uploadbox=tab.ele('xpath://*[@id="component-7"]/button')
    uploadbox.click.to_upload(file_path, by_js=None)
    chunkbox=tab.ele('xpath://*[@id="component-9"]/div[2]/div/div[1]/div/input')
    chunkbox.input('Semantic Chunking\n')
    parse_btn=tab.ele('xpath://*[@id="component-11"]')
    parse_btn.click(by_js=None)
    tab.wait.eles_loaded("""xpath://*[@id="component-20"]/div[2]/div/div/div[1]/div/div""", timeout=300)
    text=tab.ele('''xpath://*[@id="component-20"]/div[2]/div/div/div[1]/div/div''').text
    browser.quit()
    with open(f'{file_path[file_path.rfind('\\') + 1:file_path.rfind('.')]}.txt', 'w', encoding='utf-8') as file:
        file.write(text)
    return text


def parseImage(file_path):
    browser=Chromium()
    tab=browser.latest_tab
    tab.get('http://localhost:8000')
    imagebox=tab.ele('xpath://*[@id="component-25-button"]')
    imagebox.click()
    parsebox=tab.ele('xpath://*[@id="component-44-button"]')
    parsebox.click()
    uploadbox=tab.ele('xpath://*[@id="component-47"]/button')
    uploadbox.click.to_upload(file_path, by_js=None)
    parse_btn=tab.ele('xpath://*[@id="component-51"]')
    parse_btn.click(by_js=None)
    tab.wait.eles_loaded("""xpath://*[@id="component-60"]/div[2]/div/div/div[1]/div/div""", timeout=300)
    text=tab.ele('''xpath://*[@id="component-60"]/div[2]/div/div/div[1]/div/div''').text
    browser.quit()
    print(text)
    with open(f'../knowledgeBase/{file_path[file_path.rfind('\\') + 1:file_path.rfind('.')]}.txt', 'w', encoding='utf-8') as file:
        file.write(text)
    return text


def parseMedia(file_path):
    browser=Chromium()
    tab=browser.latest_tab
    tab.get('http://localhost:8000')
    mediabox=tab.ele('xpath://*[@id="component-65-button"]')
    mediabox.click()
    uploadbox=tab.ele('xpath://*[@id="component-68"]/button')
    uploadbox.click.to_upload(file_path, by_js=None)
    parse_btn=tab.ele('xpath://*[@id="component-72"]')
    parse_btn.click(by_js=None)
    text=tab.ele('''xpath://*[@id="component-80"]/div[2]/div/div/div[1]/div/div''').text
    browser.quit()
    with open(f'{file_path[file_path.rfind('\\') + 1:file_path.rfind('.')]}.txt', 'w', encoding='utf-8') as file:
        file.write(text)
    return text


def parseWebsites(webUrl):
    browser=Chromium()
    tab=browser.latest_tab
    tab.get('http://localhost:8000')
    webbox=tab.ele('xpath://*[@id="component-85-button"]')
    webbox.click()
    urlbox=tab.ele('xpath://*[@id="component-90"]/label/textarea')
    urlbox.input(webUrl)
    parse_btn=tab.ele('xpath://*[@id="component-93"]')
    parse_btn.click(by_js=None)
    tab.wait.eles_loaded("""xpath://*[@id="component-95"]/div[2]/div/span""", timeout=300)
    text=tab.ele('''xpath://*[@id="component-95"]/div[2]/div/span''').texts()
    return '\n'.join(text)


def parseEverything(unknownQuery):
    file_pattern = re.compile(r'.*\.(doc|docx|pdf|ppt|pptx)$', re.IGNORECASE)
    image_pattern = re.compile(r'.*\.(png|jpg|jpeg|tiff|bmp|heic)$',
                               re.IGNORECASE)
    media_pattern = re.compile(r'.*\.(mp4|mkv|avi|mov|mp3|wav|aac)$', re.IGNORECASE)
    if file_pattern.match(unknownQuery):
        return parseDocument(unknownQuery)
    elif image_pattern.match(unknownQuery):
        return parseImage(unknownQuery)
    elif media_pattern.match(unknownQuery):
        return parseMedia(unknownQuery)
    else:
        try:
            return parseWebsites(unknownQuery)
        except:
            return "只支持doc, docx, pdf, ppt, pptx, png, jpg, jpeg, tiff, bmp, heic, mp4, mkv, avi, mov, mp3, wav, aac和网页"
