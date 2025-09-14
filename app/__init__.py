import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from config import Config
from app.extensions import db, migrate
from app.routes import convert, search, main, cleanup


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)

    # 注册蓝图
    app.register_blueprint(main.bp)
    app.register_blueprint(convert.bp)
    app.register_blueprint(search.bp)
    app.register_blueprint(cleanup.cleanup_bp)

    # 配置日志
    # Forcefully remove all existing handlers to avoid duplicates
    for handler in app.logger.handlers[:]:
        app.logger.removeHandler(handler)
        
    log_level = app.config.get('LOG_LEVEL', logging.INFO)
    app.logger.setLevel(log_level)

    # Create a stream handler for console output
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(module)s:%(lineno)d]'))
    app.logger.addHandler(stream_handler)

    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/app.log', maxBytes=1024 * 1024 * 10, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(log_level)
        app.logger.addHandler(file_handler)

    app.logger.info('Application startup')

    return app
