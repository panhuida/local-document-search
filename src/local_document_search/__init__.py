import os
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from flask import Flask, g, request
from local_document_search.config import Config
from local_document_search.extensions import db, migrate
from local_document_search.routes import convert, search, main, cleanup


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

    # 设置日志
    setup_logging(app)

    app.logger.info('Application startup')

    return app

def setup_logging(app):
    # Forcefully remove all existing handlers to avoid duplicates
    for handler in app.logger.handlers[:]:
        app.logger.removeHandler(handler)
        
    log_level_str = app.config.get('LOG_LEVEL', 'INFO')
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    app.logger.setLevel(log_level)

    # Create a stream handler for console output (only in development)
    time_fmt = app.config.get('LOG_TIME_FORMAT', '%Y-%m-%d %H:%M:%S')
    if app.debug or os.environ.get('FLASK_ENV') == 'development':
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt=time_fmt))
        app.logger.addHandler(stream_handler)

    # File handler - Timed Rotating
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        file_handler = TimedRotatingFileHandler(
            filename=os.path.join('logs', 'app.log'),
            when='midnight',
            interval=1,
            backupCount=app.config.get('LOG_BACKUP_COUNT'),
            encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt=time_fmt))
        file_handler.setLevel(log_level)
        app.logger.addHandler(file_handler)

        # Error file handler
        error_handler = logging.FileHandler(
            os.path.join('logs', 'errors.log'),
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt=time_fmt))
        app.logger.addHandler(error_handler)

