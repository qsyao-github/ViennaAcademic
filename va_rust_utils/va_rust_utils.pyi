def initialize_static() -> None:
    """
    预热全局变量
    """

# academic_utils

## paper

def academic_utils_paper_attach(file_path: str) -> str:
    """
    附加文件内容

    在knowledgeBase和code目录下查找文件。代码文件放入对应代码框中

    Parameters
    ----------
    file_path: str
        文件路径

    Returns
    ----------
    str
        文件内容。若为代码则放入代码框
    """

def academic_utils_paper_chunk(file: str, current_user_directory: str) -> list[str]:
    """
    分段

    按换行符分段，确保每段长度大于63个字符

    Parameters
    ----------
    file_path: str
        文件路径

    Returns
    ----------
    final_list: List[str]
        分段后的文本
    """

# chat_utils

## attachment_processor

def chat_utils_attachment_processor_process_attachments(
    text: str,
    file_urls: list[str],
) -> str:
    """
    将要引用的文件格式化放到用户输入前

    Parameters
    ----------
    text: str
        用户输入
    file_urls: list[str]
        所有引用文件

    Returns
    ----------
    str
        处理后文本
    """

## media_handler
def chat_utils_media_handler_create_image_component(image_path: str) -> dict:
    """
    创建多模态信息

    Parameters
    ----------
    image_path: str
        图像文件路径

    Returns
    ----------
    dict
        多模态信息，若文件不存在，则返回空字典
    """

## tool_formatter
def chat_utils_tool_formatter_format_tools(text: str) -> str:
    """
    工具调用排版

    Parameters
    ----------
    text: str
        待处理文本

    Returns
    ----------
    str
        处理后文本
    """

# file_utils

## file_conversion

def file_utils_file_conversion_pandoc_to_markdown(
    file_basename: str,
    original_file_path: str,
    target_path: str,
) -> None:
    """
    用pandoc转换为markdown

    Parameters
    ----------
    file_basename: str
        文件名，用于指定生成文件名
    original_file_path: str
        文件路径
    target_path: str
        目标路径
    """

def file_utils_file_conversion_markdown_to_everything(
    original_path: str,
    target_path: str,
    target_ext: str,
) -> None:
    """
    将markdown文件转换为其他格式

    pdf使用typst编译，其他格式使用pandoc转换
    Parameters
    ----------
    original_path: str
        原始文件路径
    target_path: str
        目标路径
    target_ext: str
        目标文件后缀
    """

# web_utils

## arxiv_crawler

def web_utils_arxiv_crawler_extract_article(html: str) -> str:
    """
    提取Arxiv论文正文部分

    Parameters
    ----------
    html: str
        完整html

    Returns
    ----------
    str
        正文html，若没有正文则为空字符串
    """

def web_utils_arxiv_crawler_process_markdown(markdown_content: str) -> str:
    """
    清洗markdonify解析内容中的超链接和连续空行

    Parameters
    ----------
    markdown_content: str
        待清洗的markdown内容

    Returns
    ----------
    str
        清洗后的markdown内容
    """
