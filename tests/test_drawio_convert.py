import os
import tempfile
import textwrap
from app.services.drawio_converter import convert_drawio_to_markdown
from app.models import ConversionType

def _write_tmp_drawio(content: str):
    fd, path = tempfile.mkstemp(suffix='.drawio')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(content)
    return path

def test_drawio_simple_inline_model():
    xml = textwrap.dedent('''\
    <mxfile host="Electron" modified="2025-01-01T00:00:00.000Z" agent="5.0" version="20.0.2">
      <diagram id="page1" name="Page-1">
        <mxGraphModel>
          <root>
            <mxCell id="0" />
            <mxCell id="1" parent="0" />
            <mxCell id="2" value="开始" vertex="1" parent="1" />
            <mxCell id="3" value="处理步骤" vertex="1" parent="1" />
            <mxCell id="4" value="结束" vertex="1" parent="1" />
          </root>
        </mxGraphModel>
      </diagram>
    </mxfile>
    ''')
    path = _write_tmp_drawio(xml)
    try:
        md, ct = convert_drawio_to_markdown(path)
        assert ct == ConversionType.DRAWIO_TO_MD
        assert '# ' + os.path.basename(path) in md
        assert '总共 1 个页面' in md
        # All three nodes extracted
        assert '- 开始' in md
        assert '- 处理步骤' in md
        assert '- 结束' in md
    finally:
        os.remove(path)

def test_drawio_multiple_pages_and_empty():
    xml = textwrap.dedent('''\
    <mxfile>
      <diagram id="p1" name="PageA">
        <mxGraphModel>
          <root>
            <mxCell id="0" />
            <mxCell id="1" parent="0" />
            <mxCell id="2" value="NodeA" vertex="1" parent="1" />
          </root>
        </mxGraphModel>
      </diagram>
      <diagram id="p2" name="PageB">
        <mxGraphModel>
          <root>
            <mxCell id="0" />
            <mxCell id="1" parent="0" />
          </root>
        </mxGraphModel>
      </diagram>
    </mxfile>
    ''')
    path = _write_tmp_drawio(xml)
    try:
        md, ct = convert_drawio_to_markdown(path)
        assert ct == ConversionType.DRAWIO_TO_MD
        assert '总共 2 个页面，1 个文本项目' in md
        assert '## PageA' in md
        assert '- NodeA' in md
        assert '## PageB' in md
        assert '此页面没有找到文本内容' in md
    finally:
        os.remove(path)
