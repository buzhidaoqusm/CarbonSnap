"""What listing, viewing, buying and completing a sale write besides the order.

The service swallows errors from these writes, so the routes answer 200
either way. Breaking the behaviour-event write left every market API test
green except the long-view ones; these tests are what notices.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.extensions.db import db
from app.models.recommendation import UserBehaviorEvent, UserPreferenceProfile


@pytest.fixture(autouse=True)
def _keyword_topics(llm_unavailable):
    # Item topics come from keyword recall and then an LLM; with the provider
    # down the best keyword candidate is used, which keeps topics deterministic.
    return


def _events(user_id: int) -> list[tuple[str, str]]:
    rows = db.session.scalars(
        select(UserBehaviorEvent)
        .where(UserBehaviorEvent.user_id == user_id, UserBehaviorEvent.domain == "market")
        .order_by(UserBehaviorEvent.id)
    )
    return [(e.action_type, e.target_type or "") for e in rows]


def _has_profile(user_id: int) -> bool:
    return (
        db.session.scalar(
            select(UserPreferenceProfile.id).where(UserPreferenceProfile.user_id == user_id)
        )
        is not None
    )


def _item(client, headers) -> int:
    response = client.post(
        "/api/market/items",
        json={"title": "Plastic bottle crusher", "price_points": 40},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def test_listing_records_the_seller(app, client, make_auth_headers):
    seller_id, seller = make_auth_headers()

    _item(client, seller)

    with app.app_context():
        assert _events(seller_id) == [("market_item_create", "item")]
        assert _has_profile(seller_id)


def test_viewing_someone_elses_item_is_recorded(app, client, make_auth_headers):
    _, seller = make_auth_headers()
    viewer_id, viewer = make_auth_headers()
    item_id = _item(client, seller)

    assert client.get(f"/api/market/items/{item_id}", headers=viewer).status_code == 200

    with app.app_context():
        assert _events(viewer_id) == [("view", "item")]
        assert _has_profile(viewer_id)


def test_buying_and_completing_are_recorded(app, client, make_auth_headers):
    seller_id, seller = make_auth_headers()
    buyer_id, buyer = make_auth_headers(points=100)
    item_id = _item(client, seller)

    order = client.post("/api/market/orders", json={"item_id": item_id}, headers=buyer)
    order_id = order.json()["data"]["id"]
    client.patch(f"/api/market/orders/{order_id}/ship", headers=seller)
    client.patch(f"/api/market/orders/{order_id}/confirm", headers=buyer)

    with app.app_context():
        assert _events(buyer_id) == [("market_order", "order")]
        assert _events(seller_id) == [
            ("market_item_create", "item"),
            ("market_order_completed_as_seller", "order"),
        ]
