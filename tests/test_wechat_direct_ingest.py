import os
import tempfile
from run import create_app
from app.extensions import db
from app.models import Document, ConversionType
from app.services.converters import convert_to_markdown


def test_direct_html_conversion_and_insert():
    """模拟微信下载后的直接转换逻辑：创建临时HTML文件并调用转换，验证插入/更新。"""
    app = create_app()
    with app.app_context():
        html_content = """<html><head><title>测试文章</title></head><body><div id='js_content'><h1>标题</h1><p>内容段落</p></div></body></html>"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as tmp:
            tmp.write(html_content)
            tmp_path = tmp.name
        try:
            # 调用现有转换（真实逻辑里是 wechat_service 内部包装）
            res = convert_to_markdown(tmp_path, 'html')
            assert res.success
            assert res.conversion_type == ConversionType.HTML_TO_MD
            # 模拟入库
            from app.utils.file_utils import get_file_metadata
            meta = get_file_metadata(tmp_path)
            doc = Document(
                file_name=meta['file_name'], file_type=meta['file_type'], file_size=meta['file_size'],
                file_created_at=meta['file_created_at'], file_modified_time=meta['file_modified_time'],
                file_path=meta['file_path'], markdown_content=res.content, conversion_type=res.conversion_type,
                status='completed', source='公众号_测试', source_url='http://example.com'
            )
            db.session.add(doc)
            db.session.commit()
            # 查询验证
            stored = Document.query.filter_by(file_path=meta['file_path']).first()
            assert stored is not None
            assert stored.conversion_type == ConversionType.HTML_TO_MD
            assert '标题' in stored.markdown_content
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
