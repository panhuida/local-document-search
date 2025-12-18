"""
Logging utilities inspired by wechat-article-assistant: centralized configuration,
request-aware context, and consistent formatter reuse across console/file handlers.
"""
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from flask import request


DEFAULT_FMT = "%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
REQUEST_FMT = "%(asctime)s | %(levelname)s | %(name)s | %(method)s %(path)s | %(funcName)s:%(lineno)d | %(message)s"


class RequestContextFilter(logging.Filter):
    """Inject lightweight request context into log records when available."""

    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover - accessor only
        try:
            record.path = request.path
            record.method = request.method
        except Exception:
            record.path = "-"
            record.method = "-"
        return True


def _build_formatter(fmt: str, time_fmt: str) -> logging.Formatter:
    return logging.Formatter(fmt, datefmt=time_fmt)


def configure_logging(app):
    """Configure Flask app logger with console (dev) and rotating file (prod) handlers."""
    for handler in app.logger.handlers[:]:
        app.logger.removeHandler(handler)

    log_level_str = app.config.get("LOG_LEVEL", "INFO")
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    app.logger.setLevel(log_level)

    time_fmt = app.config.get("LOG_TIME_FORMAT", "%Y-%m-%d %H:%M:%S")
    fmt = app.config.get("LOG_FORMAT", DEFAULT_FMT)
    request_fmt = app.config.get("LOG_REQUEST_FORMAT", REQUEST_FMT)

    base_formatter = _build_formatter(fmt, time_fmt)
    request_formatter = _build_formatter(request_fmt, time_fmt)
    request_filter = RequestContextFilter()

    # Console handler for development
    if app.debug or os.environ.get("FLASK_ENV") == "development":
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(request_formatter)
        stream_handler.addFilter(request_filter)
        stream_handler.setLevel(log_level)
        app.logger.addHandler(stream_handler)

    # Rotating file handlers for production/testing-like runs
    if not app.debug and not app.testing:
        log_dir = app.config.get("LOG_DIR", "logs")
        os.makedirs(log_dir, exist_ok=True)

        file_handler = TimedRotatingFileHandler(
            filename=os.path.join(log_dir, "app.log"),
            when="midnight",
            interval=1,
            backupCount=app.config.get("LOG_BACKUP_COUNT", 3),
            encoding="utf-8",
        )
        file_handler.setFormatter(request_formatter)
        file_handler.setLevel(log_level)
        file_handler.addFilter(request_filter)
        app.logger.addHandler(file_handler)

        error_handler = logging.FileHandler(
            os.path.join(log_dir, "errors.log"),
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(request_formatter)
        error_handler.addFilter(request_filter)
        app.logger.addHandler(error_handler)
