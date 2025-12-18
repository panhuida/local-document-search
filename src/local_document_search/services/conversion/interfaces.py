from __future__ import annotations

from typing import Protocol
from local_document_search.services.conversion_result import ConversionResult


class ConversionService(Protocol):
    """Conversion service interface for converting files to Markdown or other targets."""

    def convert(self, file_path: str, file_type: str | None = None) -> ConversionResult:
        """Convert the given file.

        Args:
            file_path: Absolute path to the file to convert.
            file_type: Optional file extension (without dot). If omitted, implementations may derive from path.
        Returns:
            ConversionResult describing success, content, and conversion_type.
        """
        ...
