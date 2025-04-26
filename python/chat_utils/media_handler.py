"""
处理聊天中出现的图片信息
"""

from typing import Dict, Optional, Union

from va_rust_utils import chat_utils_media_handler_encode_image as encode_image


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
