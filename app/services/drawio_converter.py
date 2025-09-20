import xml.etree.ElementTree as ET
import base64
import zlib
from urllib.parse import unquote
import re
import os
from app.models import ConversionType

# Reuse logic similar to scripts/exportDrawioToMD.py but library-friendly

def _decode_drawio_data(data_text: str):
    if not data_text or not data_text.strip():
        return None
    attempts = []
    try:
        data = base64.b64decode(data_text)
        xml = zlib.decompress(data, wbits=-15).decode('utf-8')
        return unquote(xml)
    except Exception as e:
        attempts.append(e)
    try:
        data = base64.b64decode(data_text)
        xml = zlib.decompress(data).decode('utf-8')
        return unquote(xml)
    except Exception as e:
        attempts.append(e)
    try:
        return unquote(base64.b64decode(data_text).decode('utf-8'))
    except Exception as e:
        attempts.append(e)
    try:
        return unquote(data_text)
    except Exception as e:
        attempts.append(e)
    return data_text  # fallback raw

_html_entity_map = {
    '&lt;': '<', '&gt;': '>', '&amp;': '&', '&nbsp;': ' ', '&quot;': '"', '&#39;': "'"
}
_tag_pattern = re.compile(r'<[^>]+>')


def _clean_html_text(text: str) -> str:
    if not text:
        return ''
    for k,v in _html_entity_map.items():
        text = text.replace(k, v)
    text = _tag_pattern.sub('', text)
    text = ' '.join(text.split())
    return text.strip()


def _process_diagram(diagram: ET.Element):
    diagram_name = diagram.get('name', '未命名图表')
    mxGraphModel = diagram.find('mxGraphModel')
    if mxGraphModel is not None:
        xml_root = mxGraphModel
    else:
        raw = diagram.text
        if not raw:
            return diagram_name, []
        xml_content = _decode_drawio_data(raw)
        if not xml_content:
            return diagram_name, []
        try:
            xml = ET.fromstring(xml_content)
        except ET.ParseError:
            return diagram_name, []
        if xml.tag == 'mxGraphModel':
            xml_root = xml
        else:
            xml_root = xml.find('.//mxGraphModel')
            if xml_root is None:
                return diagram_name, []
    root_element = xml_root.find('root')
    if root_element is None:
        return diagram_name, []
    texts = []
    for child in root_element:
        value = child.attrib.get('value', '')
        cid = child.attrib.get('id')
        if cid in ('0','1'):
            continue
        if value and value.strip():
            cleaned = _clean_html_text(value)
            if cleaned:
                texts.append(cleaned)
    return diagram_name, texts


def convert_drawio_to_markdown(path: str):
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        diagrams = root.findall('diagram')
        if not diagrams:
            return f"# {os.path.basename(path)}\n\n未找到 diagram 元素\n", ConversionType.DRAWIO_TO_MD
        results = []
        total = 0
        for d in diagrams:
            name, texts = _process_diagram(d)
            results.append((name, texts))
            total += len(texts)
        parts = [f"# {os.path.basename(path)}", f"总共 {len(diagrams)} 个页面，{total} 个文本项目", "---"]
        for name, texts in results:
            parts.append(f"## {name}")
            if texts:
                parts.extend([f"- {t}" for t in texts])
            else:
                parts.append("*此页面没有找到文本内容*")
            parts.append("")
        markdown = "\n\n".join(parts).rstrip() + "\n"
        return markdown, ConversionType.DRAWIO_TO_MD
    except FileNotFoundError:
        return f"Draw.io 文件不存在: {path}", None
    except ET.ParseError as e:
        return f"Draw.io XML 解析失败: {e}", None
    except Exception as e:
        return f"处理 Draw.io 发生未知错误: {e}", None
