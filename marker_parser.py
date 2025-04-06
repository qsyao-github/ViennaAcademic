"""
marker转换接口
"""

from marker.config.parser import ConfigParser
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict

# 加载模型，构建转换器
config = {
    "languages": "en,zh",
    "output_format": "markdown",
    "strip_existing_ocr": True,
    "disable_image_extraction": True,
    "disable_links": True,
}
config_parser = ConfigParser(config)

converter = PdfConverter(
    config=config_parser.generate_config_dict(),
    artifact_dict=create_model_dict(),
    processor_list=config_parser.get_processors(),
    renderer=config_parser.get_renderer(),
    llm_service=config_parser.get_llm_service(),
)


def pdf_to_markdown(pdf_path: str) -> str:
    """将pdf转换为markdown

    Parameters
    ----------
    pdf_path: str
        pdf路径

    Returns
    ----------
    str
        markdown文本
    """
    rendered = converter(pdf_path)
    return rendered.markdown
