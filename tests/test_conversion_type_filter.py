from local_document_search import create_app
from local_document_search.extensions import db
from local_document_search.models import Document, ConversionType
from datetime import datetime
from local_document_search.services.search_service import SearchParams, search_documents


from local_document_search.config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

def _setup_app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
    return app



def test_conversion_type_filtering():
    app = _setup_app()
    with app.app_context():
        now = datetime.utcnow()
        docs = [
            Document(file_name='a.md', file_type='MD', file_size=1, file_created_at=now, file_modified_time=now,
                     file_path='/tmp/a.md', markdown_content='# A', conversion_type=ConversionType.DIRECT, status='completed'),
            Document(file_name='b.txt', file_type='TXT', file_size=1, file_created_at=now, file_modified_time=now,
                     file_path='/tmp/b.txt', markdown_content='# B', conversion_type=ConversionType.TEXT_TO_MD, status='completed'),
            Document(file_name='c.py', file_type='PY', file_size=1, file_created_at=now, file_modified_time=now,
                     file_path='/tmp/c.py', markdown_content='# C', conversion_type=ConversionType.CODE_TO_MD, status='completed'),
        ]
        db.session.add_all(docs)
        db.session.commit()

        params = SearchParams(conversion_types=[ConversionType.CODE_TO_MD])
        pagination = search_documents(params)
        assert pagination.total == 1
        doc = pagination.items[0] if not isinstance(pagination.items[0], tuple) else pagination.items[0][0]
        assert doc.file_name == 'c.py'

        params2 = SearchParams(conversion_types=[ConversionType.DIRECT, ConversionType.TEXT_TO_MD])
        pagination2 = search_documents(params2)
        names = [i[0].file_name if isinstance(i, tuple) else i.file_name for i in pagination2.items]
        assert set(names) == {'a.md', 'b.txt'}

