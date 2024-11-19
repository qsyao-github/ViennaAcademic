import base64
from PIL import Image


def get_total_pixels(image_path):
    with Image.open(image_path) as img:
        width, height = img.size
        total_pixels = width * height
    return total_pixels


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")
