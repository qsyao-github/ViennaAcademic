import re
import subprocess


def outputHandling(result):
    text = result.stdout if result.returncode == 0 else result.stderr
    text = text[text.find('''"text":"''') +
                8:text.find('''","images":''')]
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text).replace("\\n", "\n")
    return text


def parseDocument(file_path):
    result = subprocess.run(
        f"""curl -X POST -F "file=@{file_path}" http://192.168.1.250:8010/parse_document""",
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    return outputHandling(result)


def parseImage(file_path):
    result = subprocess.run(
        f"""curl -X POST -F "file=@{file_path}" http://192.168.1.250:8010/parse_media/image""",
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    return outputHandling(result)


def parseVideo(file_path):
    result = subprocess.run(
        f"""curl -X POST -F "file=@{file_path}" http://192.168.1.250:8010/parse_media/video""",
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    return outputHandling(result)


def parseAudio(file_path):
    result = subprocess.run(
        f"""curl -X POST -F "file=@{file_path}" http://192.168.1.250:8010/parse_media/audio""",
        shell=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    return outputHandling(result)


def parseWebsite(webUrl):
    result = subprocess.run(
        f"""curl -X POST -H "Content-Type: application/json" -d '{"url": "{webUrl}"}' http://192.168.1.250:8010/parse_website"""
    )
    return outputHandling(result)


def parseEverything(unknownQuery):
    file_pattern = re.compile(r'.*\.(doc|docx|pdf|ppt|pptx)$', re.IGNORECASE)
    image_pattern = re.compile(r'.*\.(png|jpg|jpeg|tiff|bmp|heic)$',
                               re.IGNORECASE)
    video_pattern = re.compile(r'.*\.(mp4|mkv|avi|mov)$', re.IGNORECASE)
    audio_pattern = re.compile(r'.*\.(mp3|wav|aac)$', re.IGNORECASE)
    text_extensions = {
        '.vue', '.js', '.ts', '.html', '.htm', '.css', '.jsx', '.c', '.cpp',
        '.cxx', '.cc', '.java', '.py', '.go', '.php', '.rs', '.sql', '.m',
        '.mm', '.kt', '.swift', '.pl', '.pm', '.rb', '.graphql', '.gql',
        '.cbl', '.cob', '.h', '.hpp','txt','md'
    }
    # construct text_pattern
    text_pattern = re.compile(r'.*\.(' + '|'.join(text_extensions) + ')$', re.IGNORECASE)
    if file_pattern.match(unknownQuery):
        return parseDocument(unknownQuery)
    elif image_pattern.match(unknownQuery):
        return parseImage(unknownQuery)
    elif video_pattern.match(unknownQuery):
        return parseVideo(unknownQuery)
    elif audio_pattern.match(unknownQuery):
        return parseAudio(unknownQuery)
    elif text_pattern.match(unknownQuery):
        with open(unknownQuery, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        try:
            return parseWebsite(unknownQuery)
        except:
            return "只允许上传doc, docx, pdf, ppt, pptx, png, jpg, jpeg, tiff, bmp, heic, mp4, mkv, avi, mov, mp3, wav, aac和准确网址"
