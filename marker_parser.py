from api_keys import (
    laowei_mistral_client_API_KEY,
    mistral_BASE_URL,
)
from marker.config.parser import ConfigParser
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict

config = {
    "pdftext_workers": 15,
    "llm_service": "marker.services.openai.OpenAIService",
    "use_llm": True,
    "languages": "en,zh",
    "output_format": "markdown",
    "strip_existing_ocr": True,
    "openai_base_url": mistral_BASE_URL,
    "openai_model": "mistral-small-latest",
    "openai_api_key": laowei_mistral_client_API_KEY,
}
config_parser = ConfigParser(config)

converter = PdfConverter(
    config=config_parser.generate_config_dict(),
    artifact_dict=create_model_dict(),
    processor_list=config_parser.get_processors(),
    renderer=config_parser.get_renderer(),
    llm_service=config_parser.get_llm_service(),
)


def pdf_to_markdown(pdf_path: str):
    rendered = converter(pdf_path)
    return rendered.markdown
