import base64
from typing import Dict, Optional, Union
import os


def encode_image(image_path: str) -> str:
    """Base64编码图像文件

    Parameters
    ----------
    image_path: str
        图像文件路径

    Returns
    ----------
    str
        Base64编码的图像。若文件不存在，返回空字符串
    """
    if os.path.exists(image_path):
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return ""


def create_image_component(
    image_path: str,
) -> Optional[Dict[str, Union[str, Dict[str, str]]]]:
    """创建多模态信息

    Parameters
    ----------
    image_path: str
        图像文件路径

    Returns
    ----------
    Optional[Dict]
        多模态信息，若文件不存在，则返回None
    """
    if encoded := encode_image(image_path):
        return {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{encoded}", "detail": "auto"},
        }
