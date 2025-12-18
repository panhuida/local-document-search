from __future__ import annotations

import os
from typing import Optional
from local_document_search.services.conversion.interfaces import ConversionService
from local_document_search.services.converters import convert_to_markdown
from local_document_search.services.conversion_result import ConversionResult


class DefaultConversionService(ConversionService):
    """Default conversion service that wraps existing convert_to_markdown logic."""

    def convert(self, file_path: str, file_type: Optional[str] = None) -> ConversionResult:
        resolved_type = (file_type or os.path.splitext(file_path)[1].lstrip('.')).lower()
        return convert_to_markdown(file_path, resolved_type)
