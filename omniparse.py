import requests
import base64
from PIL import Image
from io import BytesIO
#### api request ####
url = 'http://0.0.0.0:8000/parse_document'
file_path = './2408.10205v1.pdf'
def parseDocument(file_path):
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(url, files=files)

    result = response.json()
    text = result['text']
    with open("./parse_results/test.md", "w") as f:
        f.write(text)


    for raw in result['images']:
        raw_decode = base64.b64decode(raw['image'])
        image_name = raw['image_name']
        Image.open(BytesIO(raw_decode)).save(f'./parse_results/{image_name}', 'PNG')
    return text