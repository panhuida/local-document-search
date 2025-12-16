import pytest
from local_document_search import create_app
from local_document_search.services.image_converter import convert_image_to_markdown
from local_document_search.services import provider_factory

class DummyFailMarkItDown:
    def convert(self, f, **kwargs):
        raise RuntimeError('dummy failure')

class DummySuccessMarkItDown:
    class Result:
        def __init__(self):
            self.text_content = 'DUMMY OK'
    def convert(self, f, **kwargs):
        return self.Result()

@pytest.fixture
def app_ctx(tmp_path):
    app = create_app()
    app.config['TESTING'] = True
    # 设置链: openai(失败) -> local(成功使用 OCR 代码路径会依赖真实依赖, 所以改成 google-genai mock 成功)
    app.config['IMAGE_CAPTION_PROVIDER'] = 'openai'
    app.config['IMAGE_PROVIDER_CHAIN'] = ['openai', 'google-genai']
    # 创建一个临时图片文件 (最小 PNG 头, OCR 不会走到)
    img_path = tmp_path / 'test.png'
    img_path.write_bytes(b'\x89PNG\r\n\x1a\n')
    with app.app_context():
        yield app, str(img_path)


def test_provider_chain_fallback(app_ctx, monkeypatch):
    app, img_path = app_ctx

    # openai -> fail
    monkeypatch.setattr(provider_factory, '_md_instances', {
        'openai': DummyFailMarkItDown(),
        'google-genai': DummySuccessMarkItDown(),
        'local': DummySuccessMarkItDown(),
    })

    content, ctype = convert_image_to_markdown(img_path)
    assert 'DUMMY OK' in content
    assert ctype is not None


def test_chain_primary_not_in_chain_added(app_ctx, monkeypatch):
    app, img_path = app_ctx
    # 修改 config: primary = gemini, chain = only openai
    app.config['IMAGE_CAPTION_PROVIDER'] = 'google-genai'
    app.config['IMAGE_PROVIDER_CHAIN'] = ['openai']

    monkeypatch.setattr(provider_factory, '_md_instances', {
        'openai': DummyFailMarkItDown(),
        'google-genai': DummySuccessMarkItDown(),
        'local': DummySuccessMarkItDown(),
    })

    content, ctype = convert_image_to_markdown(img_path)
    assert 'DUMMY OK' in content
    assert ctype is not None

