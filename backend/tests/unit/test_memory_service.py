import json
import uuid

from werkzeug.security import generate_password_hash

from app.extensions.db import db
from app.models.ai import AIConversation, AIMessage, RecyclingCase
from app.models.market import MarketItem, Order
from app.models.user import User
from app.repositories.market import market_repository
from app.repositories.recommendation import preference_profile_repository
from app.services.ai import memory_service
from app.services.recommendation import behavior_event_service, preference_profile_service


def _make_user(username: str = "service", email: str = "service@example.com") -> User:
    unique_suffix = uuid.uuid4().hex[:8]
    user = User(
        username=f"{username}_{unique_suffix}",
        email=f"{unique_suffix}_{email}",
        password_hash=generate_password_hash("password123"),
    )
    db.session.add(user)
    db.session.flush()
    return user


def _make_recycling_case(user: User, *, waste_type_predicted: str = "battery") -> RecyclingCase:
    conversation = AIConversation(user_id=user.id, title="Behavior chat")
    db.session.add(conversation)
    db.session.flush()
    origin_message = AIMessage(
        conversation_id=conversation.id,
        role="user",
        message_type="text",
        content_text="Battery help",
        sequence_no=1,
    )
    db.session.add(origin_message)
    db.session.flush()
    case = RecyclingCase(
        user_id=user.id,
        conversation_id=conversation.id,
        origin_message_id=origin_message.id,
        waste_type_predicted=waste_type_predicted,
        confidence=0.92,
        estimated_weight_kg=0.1,
        expected_co2_saved_kg=0.2,
        expected_carbon_points=2,
    )
    db.session.add(case)
    db.session.commit()
    return case


def _make_market_item(user: User, *, title: str = "Bottle lamp") -> MarketItem:
    item = market_repository.create_item(
        seller_id=user.id,
        title=title,
        description="A creative upcycling project.",
        image_urls_json=None,
        price_points=25,
    )
    db.session.flush()
    return item


def _make_market_order(item: MarketItem, buyer: User) -> Order:
    order = market_repository.create_order(
        item_id=item.id,
        buyer_id=buyer.id,
        seller_id=item.seller_id,
        price_points=item.price_points,
    )
    db.session.flush()
    return order


class TestMemoryService:
    def test_rebuild_preferences_json_from_active_memory_items(self):
        user = _make_user()

        memory_service.create_manual_memory_item(
            user_id=user.id,
            memory_type="response_style",
            memory_key="response_style",
            value={"value": "concise"},
        )
        memory_service.create_manual_memory_item(
            user_id=user.id,
            memory_type="topic_interest",
            memory_key="battery",
            value={"topic": "battery"},
        )

        summary = memory_service.rebuild_user_preferences_summary(user.id)
        stored = json.loads(db.session.get(User, user.id).preferences_json)

        assert summary["action_preferences"]["response_style"] == "concise"
        assert (
            summary["content_interest_preferences"]["topics"][0]["topic_id"] == "battery-recycling"
        )
        assert stored["action_preferences"]["response_style"] == "concise"

    def test_behavior_profiles_are_promoted_into_preferences_json(self):
        user = _make_user("behavior", "behavior@example.com")
        case = _make_recycling_case(user, waste_type_predicted="battery")

        behavior_event_service.record_ai_recycling_case_pending_audit(
            user_id=user.id, recycling_case_id=case.id
        )
        behavior_event_service.record_ai_recycling_case_failed_audit(
            user_id=user.id, recycling_case_id=case.id
        )
        behavior_event_service.record_ai_recycling_case_passed_audit(
            user_id=user.id, recycling_case_id=case.id
        )
        preference_profile_service.recompute_user_preference_profiles(user.id)

        summary = memory_service.rebuild_user_preferences_summary(user.id)
        topic = summary["content_interest_preferences"]["topics"][0]

        assert topic["topic_id"] == "battery-recycling"
        assert topic["score"] > 0
        assert topic["event_count"] == 3

    def test_market_behavior_profiles_are_promoted_into_preferences_json(self):
        seller = _make_user("seller", "seller@example.com")
        buyer = _make_user("buyer", "buyer@example.com")
        item = _make_market_item(seller)
        order = _make_market_order(item, buyer)

        preference_profile_repository.replace_content_topic_assignments(
            domain="market",
            content_type="item",
            content_id=item.id,
            topics=[{"topic_id": "upcycling", "confidence_score": 1.0, "source": "ai_constrained"}],
        )

        behavior_event_service.record_market_view(user_id=buyer.id, item_id=item.id)
        behavior_event_service.record_market_long_view(user_id=buyer.id, item_id=item.id)
        behavior_event_service.record_market_order(
            user_id=buyer.id, order_id=order.id, item_id=item.id
        )
        preference_profile_service.recompute_user_preference_profiles(buyer.id)

        summary = memory_service.rebuild_user_preferences_summary(buyer.id)
        topic = summary["content_interest_preferences"]["topics"][0]

        assert topic["topic_id"] == "upcycling"
        assert topic["score"] > 0
        assert topic["event_count"] == 3

    def test_get_prompt_memory_summary_returns_empty_for_missing_user(self):
        assert memory_service.get_prompt_memory_summary(None) == {}

    def test_rebuild_preferences_summary_returns_empty_summary_for_missing_user(self):
        summary = memory_service.rebuild_user_preferences_summary(999)

        assert summary["action_preferences"]["response_style"] is None
        assert summary["content_interest_preferences"]["topics"] == []

    def test_delete_memory_item_rebuilds_summary(self):
        user = _make_user("delete", "delete@example.com")
        item = memory_service.create_manual_memory_item(
            user_id=user.id,
            memory_type="response_style",
            memory_key="response_style",
            value={"value": "concise"},
        )

        memory_service.delete_memory_item(item_id=item.id, user_id=user.id)
        summary = memory_service.get_prompt_memory_summary(user.id)

        assert summary["action_preferences"]["response_style"] is None
