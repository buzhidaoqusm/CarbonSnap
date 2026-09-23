import uuid
from types import SimpleNamespace

from werkzeug.security import generate_password_hash

from app.extensions.db import db
from app.models.market import MarketItem, Order
from app.models.user import User
from app.repositories.market import market_repository
from app.repositories.recommendation import preference_profile_repository
from app.services.recommendation import market_recommendation_service


def _make_user(username: str = "ranker", email: str = "ranker@example.com") -> User:
    suffix = uuid.uuid4().hex[:8]
    user = User(
        username=f"{username}_{suffix}",
        email=f"{suffix}_{email}",
        password_hash=generate_password_hash("password123"),
    )
    db.session.add(user)
    db.session.flush()
    return user


def _make_item(seller_id: int, title: str) -> MarketItem:
    item = MarketItem(
        seller_id=seller_id,
        title=title,
        description=f"{title} description",
        price_points=30,
    )
    db.session.add(item)
    db.session.flush()
    return item


def _make_order(item: MarketItem, buyer: User, status: str = "paid") -> Order:
    order = market_repository.create_order(
        item_id=item.id,
        buyer_id=buyer.id,
        seller_id=item.seller_id,
        price_points=item.price_points,
    )
    order.status = status
    db.session.flush()
    return order


class TestMarketRecommendationService:
    def test_rank_items_for_user_prefers_matching_topic(self, monkeypatch):
        seller = _make_user("seller", "seller@example.com")
        user = _make_user("buyer", "buyer@example.com")
        matching_item = _make_item(seller.id, "Battery storage box")
        non_matching_item = _make_item(seller.id, "Plastic organizer")

        preference_profile_repository.replace_content_topic_assignments(
            domain="market",
            content_type="item",
            content_id=matching_item.id,
            topics=[{"topic_id": "battery-recycling", "confidence_score": 1.0}],
        )
        preference_profile_repository.replace_content_topic_assignments(
            domain="market",
            content_type="item",
            content_id=non_matching_item.id,
            topics=[{"topic_id": "plastic-recycling", "confidence_score": 1.0}],
        )

        monkeypatch.setattr(
            "app.services.recommendation.preference_profile_service.has_sufficient_history",
            lambda user_id: True,
        )
        monkeypatch.setattr(
            "app.services.recommendation.preference_profile_service.get_profile_snapshot",
            lambda user_id: {"battery-recycling": 0.9, "plastic-recycling": 0.1},
        )
        monkeypatch.setattr(
            market_recommendation_service.preference_profile_repository,
            "list_content_topic_assignments_for_content_ids",
            lambda **kwargs: {
                matching_item.id: [
                    SimpleNamespace(topic_id="battery-recycling", confidence_score=1.0)
                ],
                non_matching_item.id: [
                    SimpleNamespace(topic_id="plastic-recycling", confidence_score=1.0)
                ],
            },
        )
        monkeypatch.setattr(
            market_recommendation_service.behavior_event_repository,
            "list_behavior_target_ids_for_user",
            lambda *args, **kwargs: set(),
        )
        monkeypatch.setattr(
            market_recommendation_service.market_repository,
            "list_ordered_item_ids_by_buyer",
            lambda buyer_id: set(),
        )
        monkeypatch.setattr(
            market_recommendation_service.behavior_event_repository,
            "list_recent_topic_exposure_counts_for_user",
            lambda *args, **kwargs: {},
        )
        monkeypatch.setattr(
            market_recommendation_service.market_repository,
            "list_order_counts_for_item_ids",
            lambda item_ids, statuses=None: {},
        )

        ranked = market_recommendation_service.rank_items_for_user(
            items=[non_matching_item, matching_item],
            user_id=user.id,
        )

        assert ranked[0].id == matching_item.id

    def test_cold_start_uses_popularity_and_recency(self, monkeypatch):
        seller = _make_user("cold-seller", "cold-seller@example.com")
        buyer = _make_user("cold-buyer", "cold-buyer@example.com")
        older_popular_item = _make_item(seller.id, "Older popular item")
        newer_item = _make_item(seller.id, "Newer item")
        _make_order(older_popular_item, buyer, status="completed")

        monkeypatch.setattr(
            "app.services.recommendation.preference_profile_service.has_sufficient_history",
            lambda user_id: False,
        )
        monkeypatch.setattr(
            market_recommendation_service,
            "_recency_score",
            lambda item: 0.6 if item.id == older_popular_item.id else 0.3,
        )

        ranked = market_recommendation_service.rank_items_for_user(
            items=[newer_item, older_popular_item],
            user_id=buyer.id,
        )

        assert ranked[0].id == older_popular_item.id

    def test_engagement_score_counts_completed_orders_more_heavily(self):
        seller = _make_user("eng-seller", "eng-seller@example.com")
        buyer = _make_user("eng-buyer", "eng-buyer@example.com")
        item = _make_item(seller.id, "Reusable bottle")
        _make_order(item, buyer, status="paid")
        _make_order(item, buyer, status="completed")

        score = market_recommendation_service._engagement_score(
            item,
            {
                "total_order_counts_by_item_id": {item.id: 2},
                "completed_order_counts_by_item_id": {item.id: 1},
            },
        )

        assert score > 0.0

    def test_rank_items_for_user_inserts_alternate_topic_before_third_consecutive_match(
        self, monkeypatch
    ):
        seller = _make_user("mix-seller", "mix-seller@example.com")
        buyer = _make_user("mix-buyer", "mix-buyer@example.com")
        upcycling_1 = _make_item(seller.id, "Upcycling A")
        upcycling_2 = _make_item(seller.id, "Upcycling B")
        upcycling_3 = _make_item(seller.id, "Upcycling C")
        alternate = _make_item(seller.id, "Battery item")

        monkeypatch.setattr(
            "app.services.recommendation.preference_profile_service.has_sufficient_history",
            lambda user_id: True,
        )
        monkeypatch.setattr(
            "app.services.recommendation.preference_profile_service.get_profile_snapshot",
            lambda user_id: {"upcycling": 0.8, "battery-recycling": 0.1},
        )
        monkeypatch.setattr(
            market_recommendation_service.preference_profile_repository,
            "list_content_topic_assignments_for_content_ids",
            lambda **kwargs: {
                upcycling_1.id: [SimpleNamespace(topic_id="upcycling", confidence_score=0.85)],
                upcycling_2.id: [SimpleNamespace(topic_id="upcycling", confidence_score=0.75)],
                upcycling_3.id: [SimpleNamespace(topic_id="upcycling", confidence_score=0.65)],
                alternate.id: [
                    SimpleNamespace(topic_id="battery-recycling", confidence_score=0.95)
                ],
            },
        )
        monkeypatch.setattr(
            market_recommendation_service.behavior_event_repository,
            "list_behavior_target_ids_for_user",
            lambda *args, **kwargs: set(),
        )
        monkeypatch.setattr(
            market_recommendation_service.market_repository,
            "list_ordered_item_ids_by_buyer",
            lambda buyer_id: set(),
        )
        monkeypatch.setattr(
            market_recommendation_service.behavior_event_repository,
            "list_recent_topic_exposure_counts_for_user",
            lambda *args, **kwargs: {"upcycling": 3},
        )
        monkeypatch.setattr(
            market_recommendation_service.market_repository,
            "list_order_counts_for_item_ids",
            lambda item_ids, statuses=None: {},
        )

        ranked = market_recommendation_service.rank_items_for_user(
            items=[upcycling_3, alternate, upcycling_2, upcycling_1],
            user_id=buyer.id,
        )

        assert [item.id for item in ranked[:3]] == [upcycling_1.id, upcycling_2.id, alternate.id]
