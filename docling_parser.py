"""
docling的接口，加入自定义设置，提高解析精度
"""
import re

from docling.backend.docling_parse_v2_backend import DoclingParseV2DocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import (
    AcceleratorDevice,
    AcceleratorOptions,
    PdfPipelineOptions,
    RapidOcrOptions,
    TableFormerMode,
)
from docling.document_converter import (
    DocumentConverter,
    ImageFormatOption,
    PdfFormatOption,
    WordFormatOption,
)
from docling.pipeline.simple_pipeline import SimplePipeline
from rapidocr_onnxruntime import RapidOCR

engine = RapidOCR()
pipeline_options = PdfPipelineOptions(
    artifacts_path="/home/laowei/model/docling-models"
)
pipeline_options.do_ocr = True
pipeline_options.accelerator_options = AcceleratorOptions(
    num_threads=20, device=AcceleratorDevice.CPU
)
pipeline_options.do_table_structure = True
pipeline_options.table_structure_options.do_cell_matching = True
pipeline_options.ocr_options = RapidOcrOptions()
pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

doc_converter = DocumentConverter(  # all of the below is optional, has internal defaults.
    allowed_formats=[
        InputFormat.PDF,
        InputFormat.IMAGE,
        InputFormat.DOCX,
        InputFormat.HTML,
        InputFormat.PPTX,
    ],  # whitelist formats, non-matching files are ignored.
    format_options={
        InputFormat.PDF: PdfFormatOption(
            pipeline_options=pipeline_options,  # pipeline options go here.
            backend=DoclingParseV2DocumentBackend,  # optional: pick an alternative backend
        ),
        InputFormat.DOCX: WordFormatOption(
            pipeline_cls=SimplePipeline  # default for office formats and HTML
        ),
        InputFormat.IMAGE: ImageFormatOption(pipeline_options=pipeline_options),
    },
)

"""去除arxiv html解析结果后的无用信息"""
ARXIV_STRIP_PATTERN = re.compile(
    r"(.*?)(?=Generated  on \w{3} \w{3} \d{2} \d{2}:\d{2}:\d{2} \d{4} by)", re.DOTALL
)


def parse_everything(file_or_url: str) -> str:
    """docling的万能接口
    
    支持pdf, docx, pptx, html, image。文档解析结果中图片用<!-- image -->表示，予以去除

    Parameters
    ----------
    file_or_url: str
        文件路径或url

    Returns
    ----------
    str
        markdown解析结果
    """
    conv_result: ConversionResult = doc_converter.convert(file_or_url)
    result = conv_result.document.export_to_markdown()
    return result.replace("<!-- image -->", "").strip()


def parse_arxiv(url: str) -> str:
    """解析arxiv论文html
    
    有结果清洗机制和异常处理机制。解析失败返回空字符串，方便arxiv模块的函数处理该错误。

    Parameters
    ----------
    url: str
        arxiv论文html的url

    Returns
    ----------
    str
        markdown解析结果
    """
    try:
        text = parse_everything(url)
        match = ARXIV_STRIP_PATTERN.search(text)
        if match is not None:
            return match.group(1).strip()
    except Exception as e:
        print(f"An error occurred: {e}")
    return ""
