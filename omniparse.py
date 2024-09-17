import requests
import base64
from PIL import Image
from io import BytesIO
import subprocess
#### api request ####
url = 'http://host.docker.internal:8000/parse_document'
file_path = './2407.07061v2.pdf'
def parseDocument(file_path):
    url = 'http://localhost:8000/parse_document'
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(url, files=files)

    result = response.json()
    text = result['text']
    with open(f"{file_path}.md", "w") as f:
        f.write(text)
    return text
def parseImage(file_path):
    url = 'http://localhost:8000/parse_media/image'
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(url, files=files)

    result = response.json()
    text = result['text']
    with open(f"{file_path}.md", "w") as f:
        f.write(text)
def parseVideo(file_path):
    url= 'http://localhost:8000/parse_media/video'
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(url, files=files)
    result = response.json()
    text = result['text']
    with open(f"{file_path}.md", "w") as f:
        f.write(text)
def parseAudio(file_path):
    url= 'http://localhost:8000/parse_media/audio'
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(url, files=files)
    result = response.json()
    text = result['text']
    with open(f"{file_path}.md", "w") as f:
        f.write(text)
def parseWebsites(webUrl):
    result =subprocess.run(['curl','-X','POST','-H','"Content-Type: application/json"','-d',f'{{"url": "{webUrl}"}}','http://0.0.0.0:8000/parse_website'],capture_output=True,text=True,shell=True,check=True,encoding='utf-8')
    return result.stdout
print(parseDocument(file_path))
