"""Flask 应用入口"""

from local_document_search import create_app


app = create_app()


def main() -> None:
    """启动内置开发服务器"""
    debug = bool(app.config.get("DEBUG") or app.config.get("FLASK_DEBUG"))
    app.logger.info("Application starting...")
    app.run(host="0.0.0.0", port=5000, debug=debug)


if __name__ == "__main__":
    main()
