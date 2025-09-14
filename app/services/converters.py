import os
import traceback
from flask import current_app
from markitdown import MarkItDown
from app.models import ConversionType

# Initialize markitdown instance
_md = MarkItDown()

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
