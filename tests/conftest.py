import pytest
from local_document_search import create_app
from local_document_search.config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

@pytest.fixture
def app():
    app = create_app(TestConfig)
    return app

@pytest.fixture
def app_context(app):
    with app.app_context():
        yield
