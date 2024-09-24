import subprocess
import re


def parseDocument(file_path):
    command = f"""curl -X POST -F "file=@/{file_path}" http://localhost:8000/parse_document"""
    result = subprocess.run(command,
                            capture_output=True,
                            text=True,
                            shell=True,
                            check=True,
                            encoding='utf-8')
    text = result.stdout
    return text


def parseImage(file_path):
    command = f"""curl -X POST -F "file=@/{file_path}" http://localhost:8000/parse_media/image"""
    result = subprocess.run(command,
                            capture_output=True,
                            text=True,
                            shell=True,
                            check=True,
                            encoding='utf-8')
    text = result.stdout
    return text


def parseVideo(file_path):
    command = f"""curl -X POST -F "file=@/{file_path}" http://localhost:8000/parse_media/video"""
    result = subprocess.run(command,
                            capture_output=True,
                            text=True,
                            shell=True,
                            check=True,
                            encoding='utf-8')
    text = result.stdout
    return text


def parseAudio(file_path):
    command = f"""curl -X POST -F "file=@/{file_path}" http://localhost:8000/parse_media/audio"""
    result = subprocess.run(command,
                            capture_output=True,
                            text=True,
                            shell=True,
                            check=True,
                            encoding='utf-8')
    text = result.stdout
    return text


def parseWebsites(webUrl):
    result = subprocess.run([
        'curl', '-X', 'POST', '-H', '"Content-Type: application/json"', '-d',
        f'{{"url": "{webUrl}"}}', 'http://0.0.0.0:8000/parse_website'
    ],
                            capture_output=True,
                            text=True,
                            shell=True,
                            check=True,
                            encoding='utf-8')
    print(result.stdout)
    return result.stdout


def parseEverything(unknownQuery):
    file_pattern = re.compile(r'.*\.(doc|docx|pdf|ppt|pptx)$', re.IGNORECASE)
    image_pattern = re.compile(r'.*\.(png|jpg|jpeg|tiff|bmp|heic)$',
                               re.IGNORECASE)
    video_pattern = re.compile(r'.*\.(mp4|mkv|avi|mov)$', re.IGNORECASE)
    audio_pattern = re.compile(r'.*\.(mp3|wav|aac)$', re.IGNORECASE)
    if file_pattern.match(unknownQuery):
        return parseDocument(unknownQuery)
    elif image_pattern.match(unknownQuery):
        return parseImage(unknownQuery)
    elif video_pattern.match(unknownQuery):
        return parseVideo(unknownQuery)
    elif audio_pattern.match(unknownQuery):
        return parseAudio(unknownQuery)
    else:
        return parseWebsites(unknownQuery)
