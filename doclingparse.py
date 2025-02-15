from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.document_converter import (DocumentConverter, PdfFormatOption,
                                        WordFormatOption, ImageFormatOption)
from docling.pipeline.simple_pipeline import SimplePipeline
from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions, TableFormerMode, AcceleratorDevice, AcceleratorOptions
from docling.backend.docling_parse_v2_backend import DoclingParseV2DocumentBackend
from docling.datamodel.document import ConversionResult
from rapidocr_onnxruntime import RapidOCR
from Drission import get_html
import re

engine = RapidOCR()
pipeline_options = PdfPipelineOptions(
    artifacts_path="/home/laowei/model/docling")
pipeline_options.do_ocr = True
pipeline_options.accelerator_options = AcceleratorOptions(
    num_threads=12, device=AcceleratorDevice.CPU)
pipeline_options.do_table_structure = True
pipeline_options.table_structure_options.do_cell_matching = True
pipeline_options.ocr_options = RapidOcrOptions()
pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

doc_converter = (
    DocumentConverter(  # all of the below is optional, has internal defaults.
        allowed_formats=[
            InputFormat.PDF,
            InputFormat.IMAGE,
            InputFormat.DOCX,
            InputFormat.HTML,
            InputFormat.PPTX,
        ],  # whitelist formats, non-matching files are ignored.
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options, # pipeline options go here.
                backend=DoclingParseV2DocumentBackend # optional: pick an alternative backend
            ),
            InputFormat.DOCX: WordFormatOption(
                pipeline_cls=SimplePipeline # default for office formats and HTML
            ),
            InputFormat.IMAGE: ImageFormatOption(pipeline_options=pipeline_options)
        },
    )
)


def parseEverything(file):
    conv_result: ConversionResult = doc_converter.convert(file)
    result = conv_result.document.export_to_markdown()
    return re.sub('<!-- image -->', '', result).strip()


def parseWebsite(url):
    success = get_html(url)
    if success:
        return parseEverything('temp.html')
    return None


def parseArxiv(url):
    success = get_html(url)
    if success:
        text = parseEverything('temp.html')
        pattern = r'\n#\s+(.*?)##### Report Github Issue'
        match = re.search(pattern, text, re.DOTALL)
        if match is not None:
            return '# ' + match.group(1).strip()
    return None
