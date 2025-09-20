import os
import traceback
from flask import current_app
from .provider_factory import get_markitdown_instance
from .video_converter import convert_video_metadata
from .drawio_converter import convert_drawio_to_markdown
from .image_converter import convert_image_to_markdown
from .xmind_converter import convert_xmind_to_markdown
from .conversion_result import ConversionResult
from . import registry
from app.models import ConversionType


# ------------ Individual Handlers (each returns ConversionResult) -------------

def _read_native_markdown(path: str, file_type: str) -> ConversionResult:
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return ConversionResult(True, content, ConversionType.DIRECT, file_path=path, file_type=file_type).sanitized()
    except (IOError, OSError) as e:
        return ConversionResult(False, None, None, error=f"Read markdown failed: {e}", file_path=path, file_type=file_type)

def _read_plain_text(path: str, file_type: str) -> ConversionResult:
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
        content = f"# {os.path.basename(path)}\n\n{text}"
        return ConversionResult(True, content, ConversionType.TEXT_TO_MD, file_path=path, file_type=file_type).sanitized()
    except (IOError, OSError) as e:
        return ConversionResult(False, None, None, error=f"Read text failed: {e}", file_path=path, file_type=file_type)

def _read_code(path: str, file_type: str) -> ConversionResult:
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
        content = f"# {os.path.basename(path)}\n\n```{file_type.lower()}\n{text}\n```"
        return ConversionResult(True, content, ConversionType.CODE_TO_MD, file_path=path, file_type=file_type).sanitized()
    except (IOError, OSError) as e:
        return ConversionResult(False, None, None, error=f"Read code failed: {e}", file_path=path, file_type=file_type)

def _convert_xmind(path: str, file_type: str) -> ConversionResult:
    content, ctype = convert_xmind_to_markdown(path)
    if ctype is None:
        return ConversionResult(False, None, None, error=content, file_path=path, file_type=file_type)
    return ConversionResult(True, content, ctype, file_path=path, file_type=file_type).sanitized()

def _convert_image(path: str, file_type: str) -> ConversionResult:
    content, ctype = convert_image_to_markdown(path)
    if ctype is None:
        return ConversionResult(False, None, None, error=content, file_path=path, file_type=file_type)
    return ConversionResult(True, content, ctype, file_path=path, file_type=file_type).sanitized()

def _convert_video(path: str, file_type: str) -> ConversionResult:
    content, ctype = convert_video_metadata(path)
    if ctype is None:
        return ConversionResult(False, None, None, error=content, file_path=path, file_type=file_type)
    return ConversionResult(True, content, ctype, file_path=path, file_type=file_type).sanitized()

def _convert_drawio(path: str, file_type: str) -> ConversionResult:
    content, ctype = convert_drawio_to_markdown(path)
    if ctype is None:
        return ConversionResult(False, None, None, error=content, file_path=path, file_type=file_type)
    return ConversionResult(True, content, ctype, file_path=path, file_type=file_type).sanitized()

def _convert_structured(path: str, file_type: str) -> ConversionResult:
    try:
        structured_md = get_markitdown_instance('local')
        with open(path, 'rb') as f:
            result = structured_md.convert(f)
        if not result.text_content or not result.text_content.strip():
            return ConversionResult(False, None, None, error=f"Empty structured conversion for {path}", file_path=path, file_type=file_type)
        # If file is html/htm assign new HTML_TO_MD conversion type
        ctype = ConversionType.HTML_TO_MD if file_type.lower() in ('html','htm') else ConversionType.STRUCTURED_TO_MD
        return ConversionResult(True, result.text_content, ctype, file_path=path, file_type=file_type).sanitized()
    except Exception as e:
        return ConversionResult(False, None, None, error=f"Structured conversion failed: {e}", file_path=path, file_type=file_type)


def _bootstrap_registry():
    cfg = current_app.config
    # map config lists to handlers
    mapping = [
        (cfg.get('NATIVE_MARKDOWN_TYPES', []), _read_native_markdown),
        (cfg.get('PLAIN_TEXT_TO_MARKDOWN_TYPES', []), _read_plain_text),
        (cfg.get('CODE_TO_MARKDOWN_TYPES', []), _read_code),
        (cfg.get('XMIND_TO_MARKDOWN_TYPES', []), _convert_xmind),
        (cfg.get('IMAGE_TO_MARKDOWN_TYPES', []), _convert_image),
        (cfg.get('VIDEO_TO_MARKDOWN_TYPES', []), _convert_video),
        (cfg.get('DRAWIO_TO_MARKDOWN_TYPES', []), _convert_drawio),
        (cfg.get('HTML_TO_MARKDOWN_TYPES', []), _convert_structured),  # 独立HTML分类
        (cfg.get('STRUCTURED_TO_MARKDOWN_TYPES', []), _convert_structured),
    ]
    for exts, handler in mapping:
        if not exts:  # pragma: no cover - defensive
            continue
        registry.register(list(exts))(handler)

_BOOTSTRAPPED = False

def convert_to_markdown(file_path: str, file_type: str) -> ConversionResult:
    global _BOOTSTRAPPED
    try:
        if not _BOOTSTRAPPED:
            _bootstrap_registry()
            _BOOTSTRAPPED = True
        handler = registry.get_handler(file_type)
        if not handler:
            current_app.logger.warning(f"[ConverterDispatch] No handler for file_type='{file_type}'. Registered keys={list(registry._handlers.keys())}")
            return ConversionResult(False, None, None, error=f"Unsupported file type: {file_type}", file_path=file_path, file_type=file_type)
        return handler(file_path, file_type)
    except Exception as e:
        return ConversionResult(False, None, None, error=f"Unexpected error: {e}\n{traceback.format_exc()}", file_path=file_path, file_type=file_type)

