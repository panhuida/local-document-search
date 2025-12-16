import os
import tempfile
from local_document_search.services.converters import convert_to_markdown
from local_document_search.models import ConversionType


def test_html_conversion_type(app_context):
    # 创建临时 HTML 文件
    html_content = """<html><head><title>Test</title></head><body><h1>Hello</h1><p>World</p></body></html>"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as tmp:
        tmp.write(html_content)
        tmp_path = tmp.name

    try:
        result = convert_to_markdown(tmp_path, file_type='html')
        assert result.success, f"Conversion failed: {result.error}"
        assert result.conversion_type == ConversionType.HTML_TO_MD, (
            f"Expected conversion_type {ConversionType.HTML_TO_MD} for HTML, got {result.conversion_type}"
        )
        assert 'Hello' in (result.content or ''), 'Converted content missing expected text.'
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)