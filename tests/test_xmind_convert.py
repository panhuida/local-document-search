import io
import os
import zipfile
import tempfile
from local_document_search.services.xmind_converter import convert_xmind_to_markdown
from local_document_search.models import ConversionType

def _make_minimal_xmind(path: str):
    # Minimal JSON structure for XMind: list with one sheet containing rootTopic
    content_json = [
        {
            "id": "sheet-1",
            "title": "Sheet 1",
            "rootTopic": {
                "id": "root-1",
                "title": "Root Topic",
                "children": {
                    "attached": [
                        {"id": "c1", "title": "Child A"},
                        {"id": "c2", "title": "Child B"}
                    ]
                }
            }
        }
    ]
    import json
    with zipfile.ZipFile(path, 'w') as zf:
        zf.writestr('content.json', json.dumps(content_json))


def test_xmind_minimal_conversion():
    with tempfile.TemporaryDirectory() as tmp:
        fp = os.path.join(tmp, 'test.xmind')
        _make_minimal_xmind(fp)
        md, ctype = convert_xmind_to_markdown(fp)
        assert ctype == ConversionType.XMIND_TO_MD
        assert md.startswith('# Root Topic')
        assert '- Child A' in md and '- Child B' in md

