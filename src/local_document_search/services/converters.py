import os
import re
import json
import zipfile
import traceback
import logging
from typing import List
from xml.etree import ElementTree as ET
from markitdown import MarkItDown
from local_document_search.config import Config
from local_document_search.models import ConversionType
from local_document_search.services.conversion_result import ConversionResult
from local_document_search.services.doc_converter import convert_doc_to_docx
from local_document_search.services.drawio_converter import convert_drawio_to_markdown
from local_document_search.services.image_converter import convert_image_to_markdown
from local_document_search.services.ppt_converter import convert_ppt_to_pptx
from local_document_search.services.video_converter import convert_video_metadata
from local_document_search.services.registry import register, get_handler

logger = logging.getLogger(__name__)

# Initialize markitdown instance (shared)
_md = MarkItDown()

class XMindLoader:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def get_content(self):
        with zipfile.ZipFile(self.file_path) as zf:
            namelist = zf.namelist()
            if "content.json" in namelist:
                content_json = zf.read("content.json").decode("utf-8")
                return json.loads(content_json), "json"
            elif "content.xml" in namelist:
                content_xml = zf.read("content.xml").decode("utf-8")
                content_xml = re.sub(r'\sxmlns(:\w+)?="[^"]+"', "", content_xml)
                content_xml = re.sub(r'\b\w+:(\w+)=(["\'][^"\']*["\'])', r"\1=\2", content_xml)
                root = ET.fromstring(content_xml)
                return root, "xml"
            else:
                raise FileNotFoundError(
                    "XMind file must contain content.json or content.xml"
                )

    @staticmethod
    def topic2md_json(topic: dict, is_root: bool = False, depth: int = -1) -> str:
        title = topic.get("title", "").replace("\r", "").replace("\n", " ")
        if is_root:
            md = "# " + title + "\n\n"
        else:
            md = depth * "  " + "- " + title + "\n"
        if "children" in topic:
            for child in topic["children"]["attached"]:
                md += XMindLoader.topic2md_json(child, depth=depth + 1)
        return md

    @staticmethod
    def topic2md_xml(topic: ET.Element, is_root: bool = False, depth: int = -1) -> str:
        title_element = topic.find("title")
        title = title_element.text.replace("\r", "").replace("\n", " ") if title_element is not None and title_element.text is not None else ""
        if is_root:
            md = "# " + title + "\n\n"
        else:
            md = depth * "  " + "- " + title + "\n"
        for child in topic.findall("children/topics[@type='attached']/topic"):
            md += XMindLoader.topic2md_xml(child, depth=depth + 1)
        return md

    def load(self) -> list[str]:
        content, format = self.get_content()

        docs: List[str] = []
        if format == "json":
            content: List[dict]
            for sheet in content:
                docs.append(
                    XMindLoader.topic2md_json(sheet["rootTopic"], is_root=True).strip(),
                )

        elif format == "xml":
            content: ET.Element
            for sheet in content.findall("sheet"):
                docs.append(
                    XMindLoader.topic2md_xml(sheet.find("topic"), is_root=True).strip(),
                )

        else:
            raise ValueError("Invalid format")

        return docs

def _read_text_file(file_path: str):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


@register(Config.NATIVE_MARKDOWN_TYPES)
def _convert_native_markdown(file_path: str, file_type: str) -> ConversionResult:
    try:
        content = _read_text_file(file_path)
        return ConversionResult(success=True, content=content, conversion_type=ConversionType.DIRECT)
    except (IOError, OSError) as e:
        return ConversionResult(success=False, error=f"Error reading native markdown file: {e}", conversion_type=None, content=None)


@register(Config.PLAIN_TEXT_TO_MARKDOWN_TYPES)
def _convert_plain_text(file_path: str, file_type: str) -> ConversionResult:
    try:
        text = _read_text_file(file_path)
        content = f"# {os.path.basename(file_path)}\n\n{text}"
        return ConversionResult(success=True, content=content, conversion_type=ConversionType.TEXT_TO_MD)
    except (IOError, OSError) as e:
        return ConversionResult(success=False, error=f"Error reading plain text file: {e}", conversion_type=None, content=None)


@register(Config.CODE_TO_MARKDOWN_TYPES)
def _convert_code(file_path: str, file_type: str) -> ConversionResult:
    try:
        text = _read_text_file(file_path)
        content = f"# {os.path.basename(file_path)}\n\n```{file_type}\n{text}\n```"
        return ConversionResult(success=True, content=content, conversion_type=ConversionType.CODE_TO_MD)
    except (IOError, OSError) as e:
        return ConversionResult(success=False, error=f"Error reading code file: {e}", conversion_type=None, content=None)


@register(Config.XMIND_TO_MARKDOWN_TYPES)
def _convert_xmind(file_path: str, file_type: str) -> ConversionResult:
    try:
        loader = XMindLoader(file_path)
        docs = loader.load()
        content = "\n\n".join(docs)
        return ConversionResult(success=True, content=content, conversion_type=ConversionType.XMIND_TO_MD)
    except Exception as e:
        return ConversionResult(success=False, error=f"XMind conversion failed: {e}", conversion_type=None, content=None)


@register(Config.IMAGE_TO_MARKDOWN_TYPES)
def _convert_image(file_path: str, file_type: str) -> ConversionResult:
    try:
        content, conversion_type = convert_image_to_markdown(file_path)
        if conversion_type is None:
            return ConversionResult(success=False, error=content, conversion_type=None, content=None)
        return ConversionResult(success=True, content=content, conversion_type=conversion_type)
    except Exception as e:
        return ConversionResult(success=False, error=f"Image conversion failed: {e}", conversion_type=None, content=None)


@register(Config.HTML_TO_MARKDOWN_TYPES)
def _convert_html(file_path: str, file_type: str) -> ConversionResult:
    try:
        with open(file_path, 'rb') as f:
            result = _md.convert(f)
        if not result.text_content or not result.text_content.strip():
            return ConversionResult(success=False, error=f"Markitdown conversion resulted in empty content for {file_path}. Error: {getattr(result, 'error', None)}", conversion_type=None, content=None)
        return ConversionResult(success=True, content=result.text_content, conversion_type=ConversionType.HTML_TO_MD)
    except Exception as e:
        return ConversionResult(success=False, error=f"HTML to Markdown conversion failed: {e}", conversion_type=None, content=None)


@register(Config.STRUCTURED_TO_MARKDOWN_TYPES)
def _convert_structured(file_path: str, file_type: str) -> ConversionResult:
    try:
        adjusted_path = file_path
        if file_type == 'doc':
            adjusted_path = convert_doc_to_docx(file_path)
            if not adjusted_path:
                return ConversionResult(success=False, error="Failed to convert .doc to .docx", conversion_type=None, content=None)
        elif file_type == 'ppt':
            adjusted_path = convert_ppt_to_pptx(file_path)
            if not adjusted_path:
                return ConversionResult(success=False, error="Failed to convert .ppt to .pptx", conversion_type=None, content=None)

        logger.debug("Attempting Markitdown conversion for structured file: %s", adjusted_path)

        if not os.path.exists(adjusted_path):
            return ConversionResult(success=False, error=f"Converted file not found: {adjusted_path}", conversion_type=None, content=None)

        with open(adjusted_path, 'rb') as f:
            result = _md.convert(f)
        logger.debug(
            "Markitdown conversion completed for %s. Content length: %s, Error: %s",
            adjusted_path,
            len(result.text_content) if result.text_content else 0,
            getattr(result, 'error', None),
        )

        if not result.text_content or not result.text_content.strip():
            return ConversionResult(success=False, error=f"Markitdown conversion resulted in empty content for {adjusted_path}. Error: {getattr(result, 'error', None)}", conversion_type=None, content=None)
        return ConversionResult(success=True, content=result.text_content, conversion_type=ConversionType.STRUCTURED_TO_MD)
    except Exception as e:
        return ConversionResult(success=False, error=f"Markitdown conversion failed: {e}", conversion_type=None, content=None)


@register(Config.VIDEO_TO_MARKDOWN_TYPES)
def _convert_video(file_path: str, file_type: str) -> ConversionResult:
    try:
        content_or_error, conv_type = convert_video_metadata(file_path)
        if conv_type is None:
            return ConversionResult(success=False, error=content_or_error, conversion_type=None, content=None)
        return ConversionResult(success=True, content=content_or_error, conversion_type=conv_type)
    except Exception as e:
        return ConversionResult(success=False, error=f"Video metadata extraction failed: {e}", conversion_type=None, content=None)


@register(Config.DRAWIO_TO_MARKDOWN_TYPES)
def _convert_drawio(file_path: str, file_type: str) -> ConversionResult:
    return convert_drawio_to_markdown(file_path)


def convert_to_markdown(file_path, file_type) -> ConversionResult:
    """
    Converts a file to Markdown format with fine-grained error handling via registered handlers.
    """
    file_type_lower = (file_type or '').lower()
    handler = get_handler(file_type_lower)
    if not handler:
        return ConversionResult(success=False, error=f"Unsupported file type: {file_type}", conversion_type=None, content=None)

    try:
        result = handler(file_path, file_type_lower)
        return result.sanitized()
    except Exception as e:
        error_message = f"An unexpected error occurred in converter for {file_path}: {e}\n{traceback.format_exc()}"
        return ConversionResult(success=False, error=error_message, conversion_type=None, content=None)

