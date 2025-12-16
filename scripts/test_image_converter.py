import sys
from pathlib import Path

# Ensure project root is on sys.path so `app` package can be imported when running
# this script directly (python scripts\test_image_converter.py)
ROOT = Path(__file__).resolve().parents[1]
src_path = ROOT / 'src'
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from local_document_search.services.image_converter import convert_image_to_markdown
from flask import Flask
app = Flask(__name__)
app.config['ENABLE_IMAGE_DESCRIPTION'] = True
app.config['IMAGE_CAPTION_PROVIDER'] = 'qwen-ocr'  # or whichever you use
with app.app_context():
    content, ctype = convert_image_to_markdown(r'E:\documents\测试\世界政治地图.webp')
    print(ctype)
    print(content[:400])
