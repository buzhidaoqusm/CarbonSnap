from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ItemOut(BaseModel):
    id: int
    seller_id: int
    title: str
    description: str | None
    # A JSON array of image URLs, stored and returned as a string.
    image_urls_json: str | None
    price_points: int
    status: str
    # Naive ISO 8601 (datetime.isoformat()), as the frontend has always had.
    created_at: str


class ItemPage(BaseModel):
    items: list[ItemOut]
    total: int
    page: int
    per_page: int


class OrderOut(BaseModel):
    id: int
    item_id: int
    buyer_id: int
    seller_id: int
    price_points: int
    status: str
    created_at: str


class OrderPage(BaseModel):
    items: list[OrderOut]
    total: int
    page: int
    per_page: int


class LongViewResult(BaseModel):
    tracked: bool
    reason: str | None = None


# Request bodies. Numbers may arrive as strings, as the Flask routes accepted;
# the route converts them and keeps the old error messages.


class ItemIn(BaseModel):
    title: str = ""
    description: str | None = None
    image_urls_json: str | None = None
    price_points: int | str = 0


class OrderIn(BaseModel):
    item_id: Any = None
