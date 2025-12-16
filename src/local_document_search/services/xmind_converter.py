import re
import json
import zipfile
from typing import List, Tuple
from xml.etree import ElementTree as ET
from local_document_search.models import ConversionType

class XMindLoader:
    """Loader to parse .xmind file (supports both JSON and XML content)."""
    def __init__(self, file_path: str):
        self.file_path = file_path

    def _get_content(self):
        with zipfile.ZipFile(self.file_path) as zf:
            namelist = zf.namelist()
            if "content.json" in namelist:
                content_json = zf.read("content.json").decode("utf-8")
                return json.loads(content_json), "json"
            elif "content.xml" in namelist:
                content_xml = zf.read("content.xml").decode("utf-8")
                # Remove namespaces for simpler parsing
                content_xml = re.sub(r'\sxmlns(:\w+)?="[^"]+"', "", content_xml)
                content_xml = re.sub(r'\b\w+:(\w+)=("[^"]*"|\'[^"]*\')', r"\1=\2", content_xml)
                root = ET.fromstring(content_xml)
                return root, "xml"
            else:
                raise FileNotFoundError("XMind file must contain content.json or content.xml")

    @staticmethod
    def _topic2md_json(topic: dict, is_root: bool = False, depth: int = -1) -> str:
        title = (topic.get("title") or "").replace("\r", "").replace("\n", " ")
        if is_root:
            md = f"# {title}\n\n"
        else:
            md = depth * "  " + f"- {title}\n"
        children_container = topic.get("children", {})
        attached = children_container.get("attached") or []
        for child in attached:
            md += XMindLoader._topic2md_json(child, depth=depth + 1)
        return md

    @staticmethod
    def _topic2md_xml(topic: ET.Element, is_root: bool = False, depth: int = -1) -> str:
        title_el = topic.find("title")
        title_text = (title_el.text if title_el is not None else "").replace("\r", "").replace("\n", " ")
        if is_root:
            md = f"# {title_text}\n\n"
        else:
            md = depth * "  " + f"- {title_text}\n"
        for child in topic.findall("children/topics[@type='attached']/topic"):
            md += XMindLoader._topic2md_xml(child, depth=depth + 1)
        return md

    def load_markdown_docs(self) -> List[str]:
        content, fmt = self._get_content()
        docs: List[str] = []
        if fmt == "json":
            for sheet in content:
                root_topic = sheet.get("rootTopic")
                if root_topic:
                    docs.append(XMindLoader._topic2md_json(root_topic, is_root=True).strip())
        elif fmt == "xml":
            for sheet in content.findall("sheet"):
                root_topic = sheet.find("topic")
                if root_topic is not None:
                    docs.append(XMindLoader._topic2md_xml(root_topic, is_root=True).strip())
        else:
            raise ValueError("Invalid XMind internal format")
        return docs

def convert_xmind_to_markdown(file_path: str) -> Tuple[str, int | None]:
    """Convert an .xmind file into markdown content.

    Returns (markdown, ConversionType.XMIND_TO_MD) or (error_message, None) on failure.
    """
    try:
        loader = XMindLoader(file_path)
        docs = loader.load_markdown_docs()
        content = "\n\n".join(docs)
        return content, ConversionType.XMIND_TO_MD
    except Exception as e:
        return f"XMind conversion failed: {e}", None

