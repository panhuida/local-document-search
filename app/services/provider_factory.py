"""Provider factory for MarkItDown instances (OpenAI / Gemini / Local).

Separated from converters to allow reuse in image_converter without circular imports.
"""
from typing import Dict
from flask import current_app
from markitdown import MarkItDown
from .gemini_adapter import build_markitdown_with_gemini
from .openai_adapter import build_markitdown_with_openai

_md_instances: Dict[str, MarkItDown] = {
    'google-genai': None,  # Gemini
    'openai': None,
    'local': None,
}

def get_markitdown_instance(provider: str) -> MarkItDown:
    provider = (provider or 'local').lower()
    if provider == 'google-genai':
        if _md_instances['google-genai'] is None:
            try:
                _md_instances['google-genai'] = build_markitdown_with_gemini()
            except Exception as e:  # pragma: no cover - defensive
                current_app.logger.warning(f"Init Gemini MarkItDown failed, fallback to local: {e}")
                _md_instances['google-genai'] = MarkItDown()
        return _md_instances['google-genai']
    if provider == 'openai':
        if _md_instances['openai'] is None:
            try:
                _md_instances['openai'] = build_markitdown_with_openai()
            except Exception as e:  # pragma: no cover
                current_app.logger.warning(f"Init OpenAI MarkItDown failed, fallback to local: {e}")
                _md_instances['openai'] = MarkItDown()
        return _md_instances['openai']
    # local
    if _md_instances['local'] is None:
        _md_instances['local'] = MarkItDown()
    return _md_instances['local']
