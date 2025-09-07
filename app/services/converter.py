import os
import traceback
from flask import current_app
from markitdown import MarkItDown
import pdfplumber

md = MarkItDown()

def convert_to_markdown(file_path, file_type):
    """将文件转换为Markdown格式"""
    try:
        file_type_lower = file_type.lower()
        if file_type_lower in current_app.config.get('NATIVE_MARKDOWN_TYPES', []):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read(), 0
        elif file_type_lower in current_app.config.get('PLAIN_TEXT_TO_MARKDOWN_TYPES', []):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                return f"# {os.path.basename(file_path)}\n\n{content}", 1
        elif file_type_lower in current_app.config.get('CODE_TO_MARKDOWN_TYPES', []):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                return f"# {os.path.basename(file_path)}\n\n```{file_type_lower}\n{content}\n```", 2
        
        # --- New PDF Handling Logic with pdfplumber ---
        elif file_type_lower == 'pdf':
            text_content = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_content += page_text + "\n\n"
            
            if not text_content or not text_content.strip():
                return f"pdfplumber failed to extract any text from {file_path}", 4
            return text_content, 3

        elif file_type_lower in current_app.config.get('STRUCTURED_TO_MARKDOWN_TYPES', []):
            # This now handles DOCX, HTML etc., but not PDF
            with open(file_path, 'rb') as f:
                result = md.convert(f)
            if not result.text_content or not result.text_content.strip():
                return f"Conversion resulted in empty content for {file_path}", 4
            return result.text_content, 3
        else:
            return f"Unsupported file type: {file_type}", 4
            
    except Exception as e:
        error_message = f"Converter failed for {file_path}: {e}\n{traceback.format_exc()}"
        return error_message, 4