import os
import re
import json
import zipfile
import traceback
from typing import List
from xml.etree import ElementTree as ET
from flask import current_app
from markitdown import MarkItDown
from .gemini_adapter import build_markitdown_with_gemini
from app.models import ConversionType

# Initialize MarkItDown instance.
# 若设置 GEMINI_API_KEY 则自动使用 Gemini 多模态描述图片，否则为普通实例。
_md = build_markitdown_with_gemini()

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
                content_xml = re.sub(r'\b\w+:(\w+)=(["\"][^"\"]*["\"])', r"\1=\2", content_xml)
                root = ET.fromstring(content_xml)
                return root, "xml"
            else:
                raise FileNotFoundError(
                    "XMind file must contain content.json or content.xml"
                )

    @staticmethod
    def topic2md_json(topic: dict, is_root: bool = False, depth: int = -1) -> str:
        title = topic["title"].replace("\r", "").replace("\n", " ")
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
        title = topic.find("title").text.replace("\r", "").replace("\n", " ")
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

def convert_to_markdown(file_path, file_type):
    """
    Converts a file to Markdown format with fine-grained error handling.
    Returns a tuple of (content, conversion_type).
    On failure, returns (error_message, None).
    """
    file_type_lower = file_type.lower()
    
    try:
        if file_type_lower in current_app.config.get('NATIVE_MARKDOWN_TYPES', []):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                conversion_type = ConversionType.DIRECT
            except (IOError, OSError) as e:
                return f"Error reading native markdown file: {e}", None

        elif file_type_lower in current_app.config.get('PLAIN_TEXT_TO_MARKDOWN_TYPES', []):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
                content = f"# {os.path.basename(file_path)}\n\n{text}"
                conversion_type = ConversionType.TEXT_TO_MD
            except (IOError, OSError) as e:
                return f"Error reading plain text file: {e}", None

        elif file_type_lower in current_app.config.get('CODE_TO_MARKDOWN_TYPES', []):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
                content = f"# {os.path.basename(file_path)}\n\n```{file_type_lower}\n{text}\n```"
                conversion_type = ConversionType.CODE_TO_MD
            except (IOError, OSError) as e:
                return f"Error reading code file: {e}", None
        
        elif file_type_lower in current_app.config.get('XMIND_TO_MARKDOWN_TYPES', []):
            try:
                loader = XMindLoader(file_path)
                docs = loader.load()
                content = "\n\n".join(docs)
                conversion_type = ConversionType.XMIND_TO_MD
            except Exception as e:
                return f"XMind conversion failed: {e}", None

        elif file_type_lower in current_app.config.get('IMAGE_TO_MARKDOWN_TYPES', []):
            try:
                llm_prompt = os.getenv('GEMINI_PROMPT') or os.getenv('GEMINI_IMAGE_PROMPT')
                convert_kwargs = {}
                if llm_prompt:
                    # 若构建实例时未带 prompt，可在此按需覆盖
                    convert_kwargs['llm_prompt'] = llm_prompt
                with open(file_path, 'rb') as f:
                    # Use MarkItDown to perform OCR / metadata and (optionally) Gemini caption
                    result = _md.convert(f, **convert_kwargs)
                
                # The result.text_content will contain the Markdown from OCR and metadata
                if not result.text_content or not result.text_content.strip():
                    # This can happen if the image has no text and no significant metadata.
                    # Instead of an error, we treat it as a success with minimal content.
                    current_app.logger.warning(f"Image conversion for {file_path} resulted in empty content. This is acceptable.")
                    content = f"# {os.path.basename(file_path)}\n\n"
                else:
                    content = result.text_content

                conversion_type = ConversionType.IMAGE_TO_MD
            except Exception as e:
                return f"Image OCR/metadata extraction failed: {e}", None

        elif file_type_lower in current_app.config.get('STRUCTURED_TO_MARKDOWN_TYPES', []):
            try:
                with open(file_path, 'rb') as f:
                    result = _md.convert(f)
                if not result.text_content or not result.text_content.strip():
                    return f"Markitdown conversion resulted in empty content for {file_path}", None
                content = result.text_content
                conversion_type = ConversionType.STRUCTURED_TO_MD
            except Exception as e:
                return f"Markitdown conversion failed: {e}", None
        else:
            return f"Unsupported file type: {file_type}", None

        sanitized_content = content.replace('\x00', '')
        return sanitized_content, conversion_type
        
    except Exception as e:
        error_message = f"An unexpected error occurred in converter for {file_path}: {e}\n{traceback.format_exc()}"
        return error_message, None

