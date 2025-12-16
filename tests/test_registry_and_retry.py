import os
import tempfile
from local_document_search import create_app
from local_document_search.extensions import db
from local_document_search.models import Document, ConversionType
from local_document_search.services.converters import convert_to_markdown
from local_document_search.services.ingestion_manager import start_session, request_cancel_ingestion, is_cancelled
from local_document_search.config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

def setup_app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
    return app



def test_convert_plain_text(tmp_path=None):
    app = setup_app()
    with app.app_context():
        with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False) as f:
            f.write('hello world')
            path = f.name
        try:
            result = convert_to_markdown(path, 'TXT')
            assert result.success
            assert 'hello world' in result.content
            assert result.conversion_type == ConversionType.TEXT_TO_MD
        finally:
            os.remove(path)


def test_retry_flow_and_session_cancel():
    app = setup_app()
    with app.app_context():
        # Create a failed doc entry (simulate failure by giving unsupported type)
        doc = Document(file_name='file.xyz', file_type='XYZ', file_size=1, file_created_at=None,
                        file_modified_time=None, file_path='/tmp/file.xyz', status='failed', error_message='init fail')
        db.session.add(doc)
        db.session.commit()

        # Retry should still fail for unsupported type
        from local_document_search.services.converters import convert_to_markdown as ctm
        result = ctm(doc.file_path, doc.file_type)
        assert not result.success
        assert 'Unsupported file type' in result.error

        # Session cancel primitives
        sid = start_session()
        assert not is_cancelled(sid)
        request_cancel_ingestion(sid)
        assert is_cancelled(sid)

