"""
处理附件替换
"""

import re

from python.academic_utils.paper import attach

"""匹配信息中的#attach{}命令"""
ATTACH_PATTERN = re.compile(r"#attach\{([^}]+)\}")


def process_attachments(text: str, current_dir: str) -> str:
    """将#attach{}命令替换为对应文件全文

    Parameters
    ----------
    text: str
        待处理文本
    current_dir: str
        当前用户根目录

    Returns
    ----------
    str
        处理后文本
    """
    return ATTACH_PATTERN.sub(lambda match: attach(match.group(1), current_dir), text)
