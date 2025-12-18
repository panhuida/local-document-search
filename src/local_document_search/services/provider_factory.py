"""Provider factory for MarkItDown instances (OpenAI / Gemini / Local) and conversion service."""
from typing import Dict, TYPE_CHECKING
from flask import current_app
from markitdown import MarkItDown
from .gemini_adapter import build_markitdown_with_gemini
from .openai_adapter import build_markitdown_with_openai
from .qwen_adapter import build_markitdown_with_qwen

if TYPE_CHECKING:  # Avoid runtime import cycles
    from local_document_search.services.conversion.interfaces import ConversionService
else:
    ConversionService = object  # runtime placeholder to satisfy type checker references

_md_instances: Dict[str, MarkItDown] = {
    'google-genai': None,  # Gemini
    'openai': None,
    'qwen-ocr': None,
    'local': None,
}

def get_markitdown_instance(provider: str) -> MarkItDown:
    provider = (provider or 'local').lower()
    if provider == 'google-genai':
        if _md_instances['google-genai'] is None:
            try:
                _md_instances['google-genai'] = build_markitdown_with_gemini()
            except Exception as e:  # pragma: no cover - defensive
                # Log detailed failure including type and repr; suggest checking env
                current_app.logger.exception(
                    "Init Gemini MarkItDown failed, fallback to local. exc_type=%s, exc=%r. Ensure GEMINI_API_KEY is set and valid.",
                    type(e).__name__, e
                )
                _md_instances['google-genai'] = MarkItDown()
        return _md_instances['google-genai']
    if provider == 'openai':
        if _md_instances['openai'] is None:
            try:
                _md_instances['openai'] = build_markitdown_with_openai()
            except Exception as e:  # pragma: no cover
                current_app.logger.exception(
                    "Init OpenAI MarkItDown failed, fallback to local. exc_type=%s, exc=%r. Ensure OPENAI_API_KEY is set and valid.",
                    type(e).__name__, e
                )
                _md_instances['openai'] = MarkItDown()
        return _md_instances['openai']
    if provider == 'qwen-ocr':
        if _md_instances['qwen-ocr'] is None:
            try:
                _md_instances['qwen-ocr'] = build_markitdown_with_qwen()
            except Exception as e:  # pragma: no cover
                current_app.logger.exception(
                    "Init Qwen-OCR MarkItDown failed, fallback to local. exc_type=%s, exc=%r. Ensure DASHSCOPE_API_KEY is set and valid.",
                    type(e).__name__, e
                )
                _md_instances['qwen-ocr'] = MarkItDown()
        return _md_instances['qwen-ocr']
    # local
    if _md_instances['local'] is None:
        _md_instances['local'] = MarkItDown()
    return _md_instances['local']


def build_conversion_service() -> ConversionService:
    """Factory for conversion service; wraps legacy convert_to_markdown for DI-friendly use."""
    from local_document_search.services.conversion.impl_default import DefaultConversionService

    return DefaultConversionService()
