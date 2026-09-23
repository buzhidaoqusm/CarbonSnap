from datetime import UTC, datetime

from app.extensions.db import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(256), nullable=False)
    avatar_url = db.Column(db.String(256))
    bio = db.Column(db.Text)
    total_carbon_amount = db.Column(db.Float, nullable=False, default=0.0)
    current_points = db.Column(db.Integer, nullable=False, default=0)
    # Compact AI-facing preference summary, stored as JSON text.
    preferences_json = db.Column(db.Text)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
