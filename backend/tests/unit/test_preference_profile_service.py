"""Unit tests for services/recommendation/preference_profile_service.py."""

import uuid
from datetime import UTC, datetime, timedelta

from werkzeug.security import generate_password_hash

from app.extensions.db import db
from app.models.ai import AIConversation, AIMessage, RecyclingCase
from app.models.forum import ForumPost
from app.models.market import MarketItem, Order
from app.models.project import Project
from app.models.user import User
from app.repositories.market import market_repository
from app.repositories.recommendation import preference_profile_repository
from app.services.recommendation import behavior_event_service, preference_profile_service


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


def _make_post(author_id: int, title: str = "Bottle post") -> ForumPost:
    post = ForumPost(
        author_id=author_id,
        title=title,
        content="How to recycle this item.",
    )
    db.session.add(post)
    db.session.flush()
    return post


def _make_recycling_case(
    user: User, *, waste_type_predicted: str = "plastic bottle"
) -> RecyclingCase:
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
        waste_type_predicted=waste_type_predicted,
        confidence=0.91,
        estimated_weight_kg=0.08,
        expected_co2_saved_kg=0.12,
        expected_carbon_points=1.2,
    )
    db.session.add(case)
    db.session.flush()
    return case


def _make_market_item(seller: User, *, title: str = "Reusable bottle craft") -> MarketItem:
    item = market_repository.create_item(
        seller_id=seller.id,
        title=title,
        description="Made from reused bottle parts.",
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


def _make_project(creator: User, *, title: str = "Community cleanup hub") -> Project:
    project = Project(
        creator_user_id=creator.id,
        title=title,
        description="A practical neighborhood sustainability project.",
        points_target=180,
        deadline_at=datetime.now(UTC) + timedelta(days=14),
    )
    db.session.add(project)
    db.session.flush()
    return project


class TestPreferenceProfileServiceHelpers:
    def test_time_decay_for_event(self):
        now = datetime.now(UTC)
        assert (
            preference_profile_service.time_decay_for_event(now - timedelta(days=3), now=now) == 1.0
        )
        assert (
            preference_profile_service.time_decay_for_event(now - timedelta(days=14), now=now)
            == 0.6
        )
        assert (
            preference_profile_service.time_decay_for_event(now - timedelta(days=40), now=now)
            == 0.3
        )

    def test_normalized_score_is_bounded(self):
        assert preference_profile_service.normalized_score(0.0) == 0.0
        assert 0.0 < preference_profile_service.normalized_score(8.0) < 1.0
        assert preference_profile_service.normalized_score(1000.0) < 1.0


class TestPreferenceProfileAggregation:
    def test_forum_topic_confidence_weights_profile_scores(self):
        user = _make_user()
        post = _make_post(user.id, title="Bottle craft")

        preference_profile_repository.replace_content_topic_assignments(
            domain="forum",
            content_type="post",
            content_id=post.id,
            topics=[
                {
                    "topic_id": "plastic-recycling",
                    "confidence_score": 0.9,
                    "source": "ai_constrained",
                },
                {"topic_id": "upcycling", "confidence_score": 0.6, "source": "ai_constrained"},
            ],
        )
        behavior_event_service.record_forum_like(
            user_id=user.id, target_type="post", target_id=post.id
        )

        profiles = preference_profile_service.recompute_user_preference_profiles(user.id)
        rows = {row.profile_key: row for row in profiles}

        assert rows["plastic-recycling"].raw_score > rows["upcycling"].raw_score
        assert rows["plastic-recycling"].normalized_score > rows["upcycling"].normalized_score
        assert 0.0 < rows["plastic-recycling"].normalized_score < 1.0

    def test_repeated_distinct_behavior_events_raise_score_but_stay_bounded(self):
        user = _make_user("repeat", "repeat@example.com")
        post = _make_post(user.id, title="Bottle sorting")

        preference_profile_repository.replace_content_topic_assignments(
            domain="forum",
            content_type="post",
            content_id=post.id,
            topics=[
                {
                    "topic_id": "plastic-recycling",
                    "confidence_score": 1.0,
                    "source": "ai_constrained",
                }
            ],
        )

        behavior_event_service.record_forum_like(
            user_id=user.id, target_type="post", target_id=post.id
        )
        first_profiles = preference_profile_service.recompute_user_preference_profiles(user.id)
        first_score = next(
            row.normalized_score for row in first_profiles if row.profile_key == "plastic-recycling"
        )

        behavior_event_service.record_forum_long_view(user_id=user.id, post_id=post.id)
        behavior_event_service.record_forum_comment_or_reply(user_id=user.id, post_id=post.id)
        second_profiles = preference_profile_service.recompute_user_preference_profiles(user.id)
        second_score = next(
            row.normalized_score
            for row in second_profiles
            if row.profile_key == "plastic-recycling"
        )

        assert second_score > first_score
        assert second_score < 1.0

    def test_like_unlike_relike_counts_as_one_active_like(self):
        user = _make_user("toggle", "toggle@example.com")
        post = _make_post(user.id, title="Plastic reuse")

        preference_profile_repository.replace_content_topic_assignments(
            domain="forum",
            content_type="post",
            content_id=post.id,
            topics=[
                {
                    "topic_id": "plastic-recycling",
                    "confidence_score": 1.0,
                    "source": "ai_constrained",
                }
            ],
        )

        behavior_event_service.record_forum_like(
            user_id=user.id, target_type="post", target_id=post.id
        )
        first_profiles = preference_profile_service.recompute_user_preference_profiles(user.id)
        first_profile = next(
            row for row in first_profiles if row.profile_key == "plastic-recycling"
        )

        behavior_event_service.record_forum_unlike(
            user_id=user.id, target_type="post", target_id=post.id
        )
        after_unlike_profiles = preference_profile_service.recompute_user_preference_profiles(
            user.id
        )

        behavior_event_service.record_forum_like(
            user_id=user.id, target_type="post", target_id=post.id
        )
        second_profiles = preference_profile_service.recompute_user_preference_profiles(user.id)
        second_profile = next(
            row for row in second_profiles if row.profile_key == "plastic-recycling"
        )

        assert after_unlike_profiles == []
        assert second_profile.raw_score == first_profile.raw_score
        assert second_profile.normalized_score == first_profile.normalized_score
        assert second_profile.event_count == first_profile.event_count == 1

    def test_ai_recycling_events_and_promotion_thresholds(self):
        user = _make_user("ai", "ai@example.com")
        case = _make_recycling_case(user, waste_type_predicted="battery")

        behavior_event_service.record_ai_recycling_case_pending_audit(
            user_id=user.id,
            recycling_case_id=case.id,
            created_at=datetime.now(UTC) - timedelta(days=2),
        )
        behavior_event_service.record_ai_recycling_case_failed_audit(
            user_id=user.id,
            recycling_case_id=case.id,
            created_at=datetime.now(UTC) - timedelta(days=1),
        )
        behavior_event_service.record_ai_recycling_case_passed_audit(
            user_id=user.id,
            recycling_case_id=case.id,
        )

        preference_profile_service.recompute_user_preference_profiles(user.id)
        promotable_topics = preference_profile_service.list_promotable_topics(user.id)
        snapshot = preference_profile_service.build_user_preference_snapshot(user.id)

        assert promotable_topics
        assert promotable_topics[0]["topic_id"] == "battery-recycling"
        assert promotable_topics[0]["event_count"] >= 3
        assert (
            snapshot["content_interest_preferences"]["topics"][0]["topic_id"] == "battery-recycling"
        )
        assert snapshot["action_preferences"]["prefer_nearby_options"] is None

    def test_market_order_weight_outscores_market_view(self):
        seller = _make_user("seller", "seller@example.com")
        buyer = _make_user("buyer", "buyer@example.com")
        item = _make_market_item(seller, title="Bottle planter")
        order = _make_market_order(item, buyer)

        preference_profile_repository.replace_content_topic_assignments(
            domain="market",
            content_type="item",
            content_id=item.id,
            topics=[{"topic_id": "upcycling", "confidence_score": 1.0, "source": "ai_constrained"}],
        )

        behavior_event_service.record_market_view(user_id=buyer.id, item_id=item.id)
        first_profiles = preference_profile_service.recompute_user_preference_profiles(buyer.id)
        first_profile = next(row for row in first_profiles if row.profile_key == "upcycling")
        first_raw_score = float(first_profile.raw_score)
        first_normalized_score = float(first_profile.normalized_score)

        behavior_event_service.record_market_order(
            user_id=buyer.id, order_id=order.id, item_id=item.id
        )
        second_profiles = preference_profile_service.recompute_user_preference_profiles(buyer.id)
        second_profile = next(row for row in second_profiles if row.profile_key == "upcycling")

        assert second_profile.raw_score > first_raw_score
        assert second_profile.normalized_score > first_normalized_score

    def test_market_item_create_contributes_to_seller_topic_profile(self):
        seller = _make_user("creator", "creator@example.com")
        item = _make_market_item(seller, title="Creative glass vase")

        preference_profile_repository.replace_content_topic_assignments(
            domain="market",
            content_type="item",
            content_id=item.id,
            topics=[{"topic_id": "upcycling", "confidence_score": 1.0, "source": "ai_constrained"}],
        )

        behavior_event_service.record_market_item_create(user_id=seller.id, item_id=item.id)
        profiles = preference_profile_service.recompute_user_preference_profiles(seller.id)

        assert any(row.profile_key == "upcycling" for row in profiles)
        row = next(row for row in profiles if row.profile_key == "upcycling")
        assert row.raw_score > 0.0
        assert row.event_count == 1

    def test_project_contribute_strengthens_project_topic_profile(self):
        creator = _make_user("project-owner", "project-owner@example.com")
        supporter = _make_user("project-supporter", "project-supporter@example.com")
        project = _make_project(creator, title="Riverside cleanup station")

        preference_profile_repository.replace_content_topic_assignments(
            domain="project",
            content_type="project",
            content_id=project.id,
            topics=[
                {
                    "topic_id": "community-cleanup",
                    "confidence_score": 1.0,
                    "source": "ai_constrained",
                }
            ],
        )

        behavior_event_service.record_project_view(user_id=supporter.id, project_id=project.id)
        first_profiles = preference_profile_service.recompute_user_preference_profiles(supporter.id)
        first_profile = next(
            row for row in first_profiles if row.profile_key == "community-cleanup"
        )
        first_raw_score = float(first_profile.raw_score)
        first_normalized_score = float(first_profile.normalized_score)

        behavior_event_service.record_project_contribute(
            user_id=supporter.id,
            project_id=project.id,
            contribution_id=101,
        )
        second_profiles = preference_profile_service.recompute_user_preference_profiles(
            supporter.id
        )
        second_profile = next(
            row for row in second_profiles if row.profile_key == "community-cleanup"
        )

        assert float(second_profile.raw_score) > first_raw_score
        assert float(second_profile.normalized_score) > first_normalized_score
