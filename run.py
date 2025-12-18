"""应用启动脚本（开发用轻量服务器）。"""

import sys
from pathlib import Path

# 添加 src 目录到 Python 路径
SRC_PATH = Path(__file__).parent / "src"
sys.path.insert(0, str(SRC_PATH))

from local_document_search import create_app

def print_banner(app):
    debug = bool(app.config.get("DEBUG") or app.config.get("FLASK_DEBUG"))
    print("=" * 60)
    print("本地文档搜索")
    print("=" * 60)
    print("服务地址: http://127.0.0.1:5000")
    print(f"调试模式: {debug}")
    print("=" * 60)
    print()


if __name__ == "__main__":
    app = create_app()
    print_banner(app)
    app.logger.info("Application starting...")
    app.logger.info("Threaded server so /convert/stop stays responsive during ingestion")

    # Flask built-in dev server; keep threaded=True to avoid blocking SSE + control endpoint
    app.run(host="127.0.0.1", port=5000, debug=app.config.get("DEBUG", False), use_reloader=False, threaded=True)

