from datetime import datetime, timezone

from app.extensions.db import db


class MarketItem(db.Model):
    __tablename__ = "market_items"

    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text)
    # JSON array of image URLs stored as text.
    image_urls_json = db.Column(db.Text)
    price_points = db.Column(db.Integer, nullable=False)
    # active | sold_out | removed
    status = db.Column(db.String(16), nullable=False, default="active")
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("market_items.id"), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    price_points = db.Column(db.Integer, nullable=False)
    # paid | shipped | completed
    status = db.Column(db.String(16), nullable=False, default="paid")
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
