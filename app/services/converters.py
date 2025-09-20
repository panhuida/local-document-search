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
from .openai_adapter import build_markitdown_with_openai
from app.models import ConversionType

# Lazy initialized provider-specific MarkItDown instances
_md_instances = {
    'google-genai': None,
    'openai': None,
    'local': None,
}

def _get_markitdown_instance(provider: str):
    provider = provider.lower()
    if provider == 'google-genai':
        if _md_instances['google-genai'] is None:
            try:
                _md_instances['google-genai'] = build_markitdown_with_gemini()
            except Exception as e:
                current_app.logger.warning(f"Init Gemini MarkItDown failed, fallback to local: {e}")
                _md_instances['google-genai'] = MarkItDown()
        return _md_instances['google-genai']
    if provider == 'openai':
        if _md_instances['openai'] is None:
            try:
                _md_instances['openai'] = build_markitdown_with_openai()
            except Exception as e:
                current_app.logger.warning(f"Init OpenAI MarkItDown failed, fallback to local: {e}")
                _md_instances['openai'] = MarkItDown()
        return _md_instances['openai']
    # local or fallback
    if _md_instances['local'] is None:
        _md_instances['local'] = MarkItDown()
    return _md_instances['local']

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
            provider = current_app.config.get('IMAGE_CAPTION_PROVIDER', 'google-genai').lower()
            try:
                if provider == 'local':
                    # Local OCR via pytesseract + optional EXIF front matter
                    try:
                        from PIL import Image, ExifTags
                        import pytesseract
                    except Exception as ie:
                        return f"Local OCR dependencies missing (Pillow / pytesseract): {ie}", None

                    # Prepare metadata containers
                    exif_data = {}
                    file_stats = None
                    sha256_hash = None

                    try:
                        # Compute file stats & hash first (single read of bytes for hash)
                        file_stats = os.stat(file_path)
                        import hashlib
                        with open(file_path, 'rb') as bf:
                            img_bytes = bf.read()
                        sha256_hash = hashlib.sha256(img_bytes).hexdigest()
                    except Exception as meta_e:
                        current_app.logger.warning(f"Failed to compute file metadata for {file_path}: {meta_e}")

                    text_blocks = []
                    with Image.open(file_path) as img:
                        # Extract EXIF if present
                        try:
                            raw_exif = img._getexif() if hasattr(img, '_getexif') else None
                            if raw_exif:
                                tag_map = {}
                                for tag_id, val in raw_exif.items():
                                    tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                                    tag_map[tag_name] = val
                                # Pick a subset of useful fields and normalize types (avoid binary data)
                                def _safe(v):
                                    # convert bytes to hex-short or str length limited
                                    if isinstance(v, bytes):
                                        if len(v) <= 32:
                                            try:
                                                return v.decode('utf-8', 'ignore')
                                            except Exception:
                                                return v.hex()[:64]
                                        return f"bytes[{len(v)}]"
                                    if isinstance(v, (list, tuple)):
                                        return [str(x) for x in v[:20]]  # limit length
                                    return v
                                wanted_keys = [
                                    'DateTimeOriginal', 'DateTime', 'Model', 'Make', 'LensModel', 'FNumber',
                                    'ExposureTime', 'ISOSpeedRatings', 'FocalLength', 'Orientation', 'Software',
                                    'GPSInfo'
                                ]
                                for k in wanted_keys:
                                    if k in tag_map:
                                        exif_data[k] = _safe(tag_map[k])
                        except Exception as exif_e:
                            current_app.logger.info(f"No EXIF data extracted for {file_path}: {exif_e}")

                        # OCR
                        lang = current_app.config.get('TESSERACT_LANG', 'eng')
                        try:
                            ocr_text = pytesseract.image_to_string(img, lang=lang)
                        except Exception as ocr_e:
                            return f"Tesseract OCR failed for {file_path}: {ocr_e}", None
                        if ocr_text and ocr_text.strip():
                            text_blocks.append(ocr_text.strip())

                        # Dimensions
                        try:
                            exif_data['Width'] = img.width
                            exif_data['Height'] = img.height
                            exif_data['Mode'] = img.mode
                            exif_data['Format'] = img.format
                        except Exception:
                            pass

                    enable_front_matter = current_app.config.get('ENABLE_IMAGE_FRONT_MATTER', True)
                    if enable_front_matter:
                        # Assemble front matter (YAML)
                        import datetime
                        front_matter = {
                            'source_file': os.path.basename(file_path),
                            'provider': 'local-ocr',
                            'hash_sha256': sha256_hash,
                            'file_size': file_stats.st_size if file_stats else None,
                            'modified_time': datetime.datetime.fromtimestamp(file_stats.st_mtime).isoformat() if file_stats else None,
                            'exif': exif_data or {},
                            'ocr_lang': current_app.config.get('TESSERACT_LANG', 'eng'),
                        }
                        # Minimal YAML serialization (avoid new dependency). Simple scalars only.
                        def _yaml_dump(d, indent=0):
                            lines = []
                            for k, v in d.items():
                                if isinstance(v, dict):
                                    lines.append(' ' * indent + f"{k}:")
                                    for sk, sv in v.items():
                                        lines.append(' ' * (indent + 2) + f"{sk}: {sv}")
                                else:
                                    lines.append(' ' * indent + f"{k}: {v}")
                            return '\n'.join(lines)
                        yaml_block = _yaml_dump(front_matter)
                        md_parts = ["---", yaml_block, "---", f"# {os.path.basename(file_path)}"]
                    else:
                        md_parts = [f"# {os.path.basename(file_path)}"]
                    if text_blocks:
                        md_parts.append('\n'.join(text_blocks))
                    content = '\n\n'.join(md_parts) + '\n'
                else:
                    # OpenAI or Google (Gemini) via MarkItDown
                    md_instance = _get_markitdown_instance(provider)
                    convert_kwargs = {}
                    # unify env prompt usage
                    prompt_env = os.getenv('IMAGE_CAPTION_PROMPT') or os.getenv('GEMINI_PROMPT') or os.getenv('GEMINI_IMAGE_PROMPT')
                    if prompt_env:
                        convert_kwargs['llm_prompt'] = prompt_env
                    with open(file_path, 'rb') as f:
                        result = md_instance.convert(f, **convert_kwargs)
                    if not result.text_content or not result.text_content.strip():
                        current_app.logger.warning(f"Image conversion for {file_path} resulted in empty content.")
                        content = f"# {os.path.basename(file_path)}\n\n"
                    else:
                        content = result.text_content
                conversion_type = ConversionType.IMAGE_TO_MD
            except Exception as e:
                return f"Image OCR/caption extraction failed ({provider}): {e}", None

        elif file_type_lower in current_app.config.get('STRUCTURED_TO_MARKDOWN_TYPES', []):
            try:
                # Structured 文档与图片 caption provider 无关，用一个本地 MarkItDown 实例即可
                structured_md = _get_markitdown_instance('local')
                with open(file_path, 'rb') as f:
                    result = structured_md.convert(f)
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

