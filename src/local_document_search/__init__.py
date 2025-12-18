import os
from flask import Flask
from local_document_search.config import Config, load_environment
from local_document_search.extensions import db, migrate
from local_document_search.routes import convert, search, main, cleanup
from local_document_search.utils.logger import configure_logging


def init_extensions(app: Flask) -> None:
    """Initialize Flask extensions."""
    db.init_app(app)
    migrate.init_app(app, db)


def register_blueprints(app: Flask) -> None:
    """Register application blueprints."""
    app.register_blueprint(main.bp)
    app.register_blueprint(convert.bp)
    app.register_blueprint(search.bp)
    app.register_blueprint(cleanup.cleanup_bp)


def create_app(config_class: type[Config] = Config) -> Flask:
    """Flask application factory."""
    load_environment()
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Refresh DB URI from environment after load_environment, since Config is evaluated at import time
    db_uri = os.environ.get('DATABASE_URL')
    if db_uri:
        app.config['SQLALCHEMY_DATABASE_URI'] = db_uri

    # Fail fast if DB URI missing to provide clearer diagnostics
    if not app.config.get('SQLALCHEMY_DATABASE_URI'):
        raise RuntimeError("SQLALCHEMY_DATABASE_URI is not set. Ensure DATABASE_URL is defined in the environment/.env.")

    init_extensions(app)
    register_blueprints(app)

    configure_logging(app)
    app.logger.info('Application startup')

    return app


# Expose a default app instance for WSGI/CLI conveniences
from local_document_search.app import app  # noqa: E402,F401
