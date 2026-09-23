from datetime import UTC, datetime

from app.extensions.db import db


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # earn | spend
    type = db.Column(db.String(16), nullable=False)
    # Absolute value (always positive). Use `type` to determine direction.
    points_delta = db.Column(db.Integer, nullable=False)
    # 0 if not a carbon-related transaction.
    co2_delta_kg = db.Column(db.Float, nullable=False, default=0.0)
    # waste_analysis | project | market_order
    source_type = db.Column(db.String(32), nullable=False)
    source_id = db.Column(db.Integer)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
