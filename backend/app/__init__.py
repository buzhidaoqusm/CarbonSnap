from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate

# Import all models at module level so Flask-Migrate can detect them.
import app.models  # noqa: F401
from app.api.ai.chat import ai_bp
from app.api.ai.memory import ai_memory_bp
from app.api.forum.routes import forum_bp
from app.api.health import health_bp
from app.api.ledger.routes import ledger_bp
from app.api.market.routes import market_bp
from app.api.notification.routes import notification_bp
from app.api.profile.auth import auth_bp
from app.api.project.routes import project_bp
from app.api.uploads.routes import uploads_bp
from app.config.settings import load_app_settings
from app.extensions.db import db
from app.extensions.jwt import jwt


def create_app() -> Flask:
    flask_app = Flask(__name__)
    load_app_settings(flask_app)

    db.init_app(flask_app)
    Migrate(flask_app, db)
    jwt.init_app(flask_app)

    # Allow local frontend development access.
    CORS(flask_app, resources={r"/api/*": {"origins": "*"}})

    flask_app.register_blueprint(health_bp, url_prefix="/api")
    flask_app.register_blueprint(ai_bp, url_prefix="/api")
    flask_app.register_blueprint(ai_memory_bp, url_prefix="/api")
    flask_app.register_blueprint(auth_bp, url_prefix="/api")
    flask_app.register_blueprint(ledger_bp, url_prefix="/api")
    flask_app.register_blueprint(forum_bp, url_prefix="/api")
    flask_app.register_blueprint(notification_bp, url_prefix="/api")
    flask_app.register_blueprint(market_bp, url_prefix="/api")
    flask_app.register_blueprint(project_bp, url_prefix="/api")
    flask_app.register_blueprint(uploads_bp, url_prefix="/api")

    return flask_app
