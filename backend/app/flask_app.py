"""The Flask app, kept only for the tests and scripts that still build one.

Nothing serves requests through it any more; it goes once they have moved
to plain SQLAlchemy sessions.
"""

from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate

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

    return flask_app
