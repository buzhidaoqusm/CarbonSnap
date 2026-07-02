"""Unit tests for services/recommendation/behavior_event_service.py."""

import json
import uuid
from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash

from app.extensions.db import db
from app.models.ai import AIConversation, AIMessage, RecyclingCase
from app.models.forum import ForumPost
from app.models.market import MarketItem, Order
from app.models.project import Project
from app.models.recommendation import UserBehaviorEvent
from app.models.user import User
from app.repositories.market import market_repository
from app.repositories.recommendation import preference_profile_repository
from app.services.recommendation import behavior_event_service


def _make_user(username: str = "alice", email: str = "alice@example.com") -> User:
    unique_suffix = uuid.uuid4().hex[:8]
    user = User(
        username=f"{username}_{unique_suffix}",
        email=f"{unique_suffix}_{email}",
        password_hash=generate_password_hash("password123"),
    )
    db.session.add(user)
    db.session.flush()
    return user


def _make_post(author_id: int, title: str = "Bottle tips") -> ForumPost:
    post = ForumPost(
        author_id=author_id,
        title=title,
        content="Recycle it carefully.",
    )
    db.session.add(post)
    db.session.flush()
    return post


def _make_recycling_case(user: User) -> RecyclingCase:
    conversation = AIConversation(user_id=user.id, title="Recycling chat")
    db.session.add(conversation)
    db.session.flush()

    origin_message = AIMessage(
        conversation_id=conversation.id,
        role="user",
        message_type="text",
        content_text="Please analyze this item.",
        sequence_no=1,
    )
    db.session.add(origin_message)
    db.session.flush()

    case = RecyclingCase(
        user_id=user.id,
        conversation_id=conversation.id,
        origin_message_id=origin_message.id,
        waste_type_predicted="plastic bottle",
        confidence=0.91,
        estimated_weight_kg=0.08,
        expected_co2_saved_kg=0.12,
        expected_carbon_points=1.2,
    )
    db.session.add(case)
    db.session.flush()
    return case


def _make_market_item(seller: User, title: str = "Reusable bottle") -> MarketItem:
    item = market_repository.create_item(
        seller_id=seller.id,
        title=title,
        description="A lightly used reusable bottle.",
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


def _make_project(creator: User, title: str = "Neighborhood cleanup") -> Project:
    project = Project(
        creator_user_id=creator.id,
        title=title,
        description="A practical community sustainability project.",
        points_target=150,
        deadline_at=datetime.now(timezone.utc) + timedelta(days=10),
    )
    db.session.add(project)
    db.session.flush()
    return project


class TestBehaviorEventService:
    def test_record_forum_like_creates_behavior_event(self):
        user = _make_user()
        post = _make_post(user.id)
        db.session.commit()

        event = behavior_event_service.record_forum_like(
            user_id=user.id,
            target_type="post",
            target_id=post.id,
        )

        persisted = db.session.get(UserBehaviorEvent, event.id)
        assert persisted is not None
        assert persisted.user_id == user.id
        assert persisted.domain == "forum"
        assert persisted.action_type == "like"
        assert persisted.target_type == "post"
        assert persisted.target_id == post.id

    def test_record_forum_unlike_creates_behavior_event(self):
        user = _make_user("unliker", "unliker@example.com")
        post = _make_post(user.id)
        db.session.commit()

        event = behavior_event_service.record_forum_unlike(
            user_id=user.id,
            target_type="post",
            target_id=post.id,
        )

        persisted = db.session.get(UserBehaviorEvent, event.id)
        assert persisted is not None
        assert persisted.user_id == user.id
        assert persisted.domain == "forum"
        assert persisted.action_type == "unlike"
        assert persisted.target_type == "post"
        assert persisted.target_id == post.id

    def test_record_forum_comment_or_reply_uses_post_id_target(self):
        user = _make_user("commenter", "commenter@example.com")
        post = _make_post(user.id)
        db.session.commit()

        event = behavior_event_service.record_forum_comment_or_reply(
            user_id=user.id,
            post_id=post.id,
        )

        assert event.domain == "forum"
        assert event.action_type == "comment_or_reply"
        assert event.target_id == post.id

    def test_record_forum_long_view_creates_behavior_event(self):
        user = _make_user("reader", "reader@example.com")
        post = _make_post(user.id)
        db.session.commit()

        event = behavior_event_service.record_forum_long_view(
            user_id=user.id,
            post_id=post.id,
        )

        persisted = db.session.get(UserBehaviorEvent, event.id)
        assert persisted is not None
        assert persisted.domain == "forum"
        assert persisted.action_type == "long_view"
        assert persisted.target_type == "post"
        assert persisted.target_id == post.id

    def test_record_ai_recycling_case_passed_audit_creates_behavior_event(self):
        user = _make_user("recycler", "recycler@example.com")
        case = _make_recycling_case(user)
        db.session.commit()

        event = behavior_event_service.record_ai_recycling_case_passed_audit(
            user_id=user.id,
            recycling_case_id=case.id,
        )

        persisted = db.session.get(UserBehaviorEvent, event.id)
        assert persisted is not None
        assert persisted.domain == "ai"
        assert persisted.action_type == "recycling_case_passed_audit"
        assert persisted.target_type == "recycling_case"
        assert persisted.target_id == case.id

    def test_record_ai_accept_creates_behavior_event(self):
        user = _make_user("acceptor", "acceptor@example.com")

        event = behavior_event_service.record_ai_accept(user_id=user.id, target_id=1234)

        assert event.domain == "ai"
        assert event.action_type == "ai_accept"
        assert event.target_id == 1234

    def test_record_market_view_uses_market_item_topics(self):
        seller = _make_user("seller", "seller@example.com")
        buyer = _make_user("buyer", "buyer@example.com")
        item = _make_market_item(seller)
        preference_profile_repository.replace_content_topic_assignments(
            domain="market",
            content_type="item",
            content_id=item.id,
            topics=[{"topic_id": "upcycling", "confidence_score": 0.8}],
        )

        event = behavior_event_service.record_market_view(user_id=buyer.id, item_id=item.id)

        persisted = db.session.get(UserBehaviorEvent, event.id)
        assert persisted is not None
        assert persisted.domain == "market"
        assert persisted.action_type == "view"
        assert persisted.target_type == "item"
        assert persisted.target_id == item.id
        assert json.loads(persisted.topic_payload_json) == [
            {"topic_id": "upcycling", "confidence_score": 0.8}
        ]
        assert json.loads(persisted.context_json) == {"item_id": item.id, "seller_id": seller.id}

    def test_record_market_long_view_falls_back_to_uncategorized(self):
        seller = _make_user("longseller", "longseller@example.com")
        viewer = _make_user("longviewer", "longviewer@example.com")
        item = _make_market_item(seller, title="No topic item")

        event = behavior_event_service.record_market_long_view(user_id=viewer.id, item_id=item.id)

        persisted = db.session.get(UserBehaviorEvent, event.id)
        assert persisted is not None
        assert persisted.domain == "market"
        assert persisted.action_type == "long_view"
        assert persisted.target_type == "item"
        assert persisted.target_id == item.id
        assert json.loads(persisted.topic_payload_json) == [
            {"topic_id": "uncategorized", "confidence_score": 1.0}
        ]

    def test_record_market_order_creates_behavior_event(self):
        seller = _make_user("orderseller", "orderseller@example.com")
        buyer = _make_user("orderbuyer", "orderbuyer@example.com")
        item = _make_market_item(seller)
        order = _make_market_order(item, buyer)
        preference_profile_repository.replace_content_topic_assignments(
            domain="market",
            content_type="item",
            content_id=item.id,
            topics=[{"topic_id": "battery-recycling", "confidence_score": 1.0}],
        )

        event = behavior_event_service.record_market_order(
            user_id=buyer.id,
            order_id=order.id,
            item_id=item.id,
        )

        persisted = db.session.get(UserBehaviorEvent, event.id)
        assert persisted is not None
        assert persisted.domain == "market"
        assert persisted.action_type == "market_order"
        assert persisted.target_type == "order"
        assert persisted.target_id == order.id
        assert json.loads(persisted.context_json) == {
            "order_id": order.id,
            "item_id": item.id,
            "seller_id": seller.id,
        }

    def test_record_market_item_create_creates_behavior_event(self):
        seller = _make_user("creator", "creator@example.com")
        item = _make_market_item(seller)

        event = behavior_event_service.record_market_item_create(user_id=seller.id, item_id=item.id)

        persisted = db.session.get(UserBehaviorEvent, event.id)
        assert persisted is not None
        assert persisted.domain == "market"
        assert persisted.action_type == "market_item_create"
        assert persisted.target_type == "item"
        assert persisted.target_id == item.id
        assert json.loads(persisted.context_json) == {
            "item_id": item.id,
            "price_points": item.price_points,
        }

    def test_record_market_order_completed_as_seller_creates_behavior_event(self):
        seller = _make_user("completedseller", "completedseller@example.com")
        buyer = _make_user("completedbuyer", "completedbuyer@example.com")
        item = _make_market_item(seller)
        order = _make_market_order(item, buyer)

        event = behavior_event_service.record_market_order_completed_as_seller(
            user_id=seller.id,
            order_id=order.id,
            item_id=item.id,
        )

        persisted = db.session.get(UserBehaviorEvent, event.id)
        assert persisted is not None
        assert persisted.domain == "market"
        assert persisted.action_type == "market_order_completed_as_seller"
        assert persisted.target_type == "order"
        assert persisted.target_id == order.id
        assert json.loads(persisted.context_json) == {
            "order_id": order.id,
            "item_id": item.id,
            "buyer_id": buyer.id,
        }

    def test_record_project_view_and_contribute_use_project_topics(self):
        creator = _make_user("projectcreator", "projectcreator@example.com")
        supporter = _make_user("projectsupporter", "projectsupporter@example.com")
        project = _make_project(creator)
        preference_profile_repository.replace_content_topic_assignments(
            domain="project",
            content_type="project",
            content_id=project.id,
            topics=[{"topic_id": "community-cleanup", "confidence_score": 0.9}],
        )

        view_event = behavior_event_service.record_project_view(user_id=supporter.id, project_id=project.id)
        contribute_event = behavior_event_service.record_project_contribute(
            user_id=supporter.id,
            project_id=project.id,
            contribution_id=77,
        )

        persisted_view = db.session.get(UserBehaviorEvent, view_event.id)
        persisted_contribute = db.session.get(UserBehaviorEvent, contribute_event.id)

        assert persisted_view.domain == "project"
        assert persisted_view.action_type == "view"
        assert persisted_view.target_type == "project"
        assert json.loads(persisted_view.topic_payload_json) == [
            {"topic_id": "community-cleanup", "confidence_score": 0.9}
        ]

        assert persisted_contribute.domain == "project"
        assert persisted_contribute.action_type == "project_contribute"
        assert persisted_contribute.target_type == "project"
        assert json.loads(persisted_contribute.context_json) == {
            "project_id": project.id,
            "contribution_id": 77,
            "creator_user_id": creator.id,
        }
