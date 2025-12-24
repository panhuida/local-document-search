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
    app.logger.info("Enabling threaded server so that /convert/stop can respond while ingestion stream is active")
    # Use run_simple with threaded=True (Werkzeug) to avoid single-thread blocking SSE + control endpoint
    run_simple("0.0.0.0", 5000, app, use_reloader=True, request_handler=ISORequestHandler, threaded=True)
