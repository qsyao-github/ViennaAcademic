"""
marker转换接口
"""

import asyncio
from marker.config.parser import ConfigParser
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict


# 加载模型，构建转换器
config = {
    "languages": "en,zh",
    "output_format": "markdown",
    "strip_existing_ocr": True,
    "format_lines": True,
    "disable_image_extraction": True,
    "disable_links": True,
    "disable_tqdm": True,
    # Test features from here
    # "redo_inline_math": True,
    # "use_llm": True,
    # "llm_service": "marker.services.openai.OpenAIService",
    # "openai_model": "",
    # "openai_api_key": "",
    # "openai_base_url": "",
}
config_parser = ConfigParser(config)

converter = PdfConverter(
    config=config_parser.generate_config_dict(),
    artifact_dict=create_model_dict(),
    processor_list=config_parser.get_processors(),
    renderer=config_parser.get_renderer(),
    llm_service=config_parser.get_llm_service(),
)


def _pdf_to_markdown(pdf_path: str) -> str:
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


async def pdf_to_markdown(pdf_path: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _pdf_to_markdown, pdf_path)
