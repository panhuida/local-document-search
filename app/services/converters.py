import os
import re
import json
import zipfile
import traceback
from typing import List
from xml.etree import ElementTree as ET
from flask import current_app
from markitdown import MarkItDown
from app.models import ConversionType
from app.services.conversion_result import ConversionResult
from app.services.doc_converter import convert_doc_to_docx
from app.services.drawio_converter import convert_drawio_to_markdown
from app.services.image_converter import convert_image_to_markdown
from app.services.ppt_converter import convert_ppt_to_pptx
from app.services.video_converter import convert_video_metadata

# Initialize markitdown instance
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

def convert_to_markdown(file_path, file_type) -> ConversionResult:
    """
    Converts a file to Markdown format with fine-grained error handling.
    Returns a ConversionResult object.
    """
    file_type_lower = file_type.lower()
    
    try:
        if file_type_lower in current_app.config.get('NATIVE_MARKDOWN_TYPES', []):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                conversion_type = ConversionType.DIRECT
            except (IOError, OSError) as e:
                return ConversionResult(success=False, error=f"Error reading native markdown file: {e}", conversion_type=None, content=None)

        elif file_type_lower in current_app.config.get('PLAIN_TEXT_TO_MARKDOWN_TYPES', []):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
                content = f"# {os.path.basename(file_path)}\n\n{text}"
                conversion_type = ConversionType.TEXT_TO_MD
            except (IOError, OSError) as e:
                return ConversionResult(success=False, error=f"Error reading plain text file: {e}", conversion_type=None, content=None)

        elif file_type_lower in current_app.config.get('CODE_TO_MARKDOWN_TYPES', []):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
                content = f"# {os.path.basename(file_path)}\n\n```{file_type_lower}\n{text}\n```"
                conversion_type = ConversionType.CODE_TO_MD
            except (IOError, OSError) as e:
                return ConversionResult(success=False, error=f"Error reading code file: {e}", conversion_type=None, content=None)
        
        elif file_type_lower in current_app.config.get('XMIND_TO_MARKDOWN_TYPES', []):
            try:
                loader = XMindLoader(file_path)
                docs = loader.load()
                content = "\n\n".join(docs)
                conversion_type = ConversionType.XMIND_TO_MD
            except Exception as e:
                return ConversionResult(success=False, error=f"XMind conversion failed: {e}", conversion_type=None, content=None)

        elif file_type_lower in current_app.config.get('IMAGE_TO_MARKDOWN_TYPES', []):
            try:
                # Centralized call to the image converter
                content, conversion_type = convert_image_to_markdown(file_path)
                if conversion_type is None:
                    # The image converter returns None for conversion_type on failure
                    return ConversionResult(success=False, error=content, conversion_type=None, content=None)
            except Exception as e:
                return ConversionResult(success=False, error=f"Image conversion failed: {e}", conversion_type=None, content=None)

        elif file_type_lower in current_app.config.get('HTML_TO_MARKDOWN_TYPES', []):
            try:
                with open(file_path, 'rb') as f:
                    result = _md.convert(f)
                
                if not result.text_content or not result.text_content.strip():
                    return ConversionResult(success=False, error=f"Markitdown conversion resulted in empty content for {file_path}. Error: {getattr(result, 'error', None)}", conversion_type=None, content=None)
                
                content = result.text_content
                conversion_type = ConversionType.HTML_TO_MD
            except Exception as e:
                return ConversionResult(success=False, error=f"HTML to Markdown conversion failed: {e}", conversion_type=None, content=None)

        elif file_type_lower in current_app.config.get('STRUCTURED_TO_MARKDOWN_TYPES', []):
            try:
                if file_type_lower == 'doc':
                    docx_path = convert_doc_to_docx(file_path)
                    if not docx_path:
                        return ConversionResult(success=False, error="Failed to convert .doc to .docx", conversion_type=None, content=None)
                    file_path = docx_path # Continue with the new .docx path
                elif file_type_lower == 'ppt':
                    pptx_path = convert_ppt_to_pptx(file_path)
                    if not pptx_path:
                        return ConversionResult(success=False, error="Failed to convert .ppt to .pptx", conversion_type=None, content=None)
                    file_path = pptx_path # Continue with the new .pptx path

                current_app.logger.debug(f"Attempting Markitdown conversion for structured file: {file_path}")
                
                if not os.path.exists(file_path):
                    return ConversionResult(success=False, error=f"Converted file not found: {file_path}", conversion_type=None, content=None)

                with open(file_path, 'rb') as f:
                    result = _md.convert(f)
                current_app.logger.debug(f"Markitdown conversion completed for {file_path}. Content length: {len(result.text_content) if result.text_content else 0}, Error: {getattr(result, 'error', None)}")

                if not result.text_content or not result.text_content.strip():
                    return ConversionResult(success=False, error=f"Markitdown conversion resulted in empty content for {file_path}. Error: {getattr(result, 'error', None)}", conversion_type=None, content=None)
                content = result.text_content
                conversion_type = ConversionType.STRUCTURED_TO_MD
            except Exception as e:
                return ConversionResult(success=False, error=f"Markitdown conversion failed: {e}", conversion_type=None, content=None)
        
        elif file_type_lower in current_app.config.get('VIDEO_TO_MARKDOWN_TYPES', []):
            try:
                # convert_video_metadata returns (content, type) or (error, None)
                content_or_error, conv_type = convert_video_metadata(file_path)
                if conv_type is None:
                    # This means an error occurred
                    return ConversionResult(success=False, error=content_or_error, conversion_type=None, content=None)
                else:
                    # Success
                    return ConversionResult(success=True, content=content_or_error, conversion_type=conv_type)
            except Exception as e:
                return ConversionResult(success=False, error=f"Video metadata extraction failed: {e}", conversion_type=None, content=None)
        
        elif file_type_lower in current_app.config.get('DRAWIO_TO_MARKDOWN_TYPES', []):
            return convert_drawio_to_markdown(file_path)

        else:
            return ConversionResult(success=False, error=f"Unsupported file type: {file_type}", conversion_type=None, content=None)

        sanitized_content = content.replace('\x00', '')
        return ConversionResult(success=True, content=sanitized_content, conversion_type=conversion_type)
        
    except Exception as e:
        error_message = f"An unexpected error occurred in converter for {file_path}: {e}\n{traceback.format_exc()}"
        return ConversionResult(success=False, error=error_message, conversion_type=None, content=None)
