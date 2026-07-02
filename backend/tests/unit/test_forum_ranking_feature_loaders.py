from datetime import datetime, timedelta, timezone
import uuid

from werkzeug.security import generate_password_hash

from app.extensions.db import db
from app.models.forum import ForumPost
from app.models.user import User
from app.repositories.forum import forum_repository
from app.repositories.recommendation import behavior_event_repository, preference_profile_repository


def _make_user(username: str = "rank-loader", email: str = "rank-loader@example.com") -> User:
    suffix = uuid.uuid4().hex[:8]
    user = User(
        username=f"{username}_{suffix}",
        email=f"{suffix}_{email}",
        password_hash=generate_password_hash("password123"),
    )
    db.session.add(user)
    db.session.flush()
    return user


def _make_post(author_id: int, title: str) -> ForumPost:
    post = ForumPost(author_id=author_id, title=title, content="content")
    db.session.add(post)
    db.session.flush()
    return post


class TestForumRankingFeatureLoaders:
    def test_list_content_topic_assignments_for_content_ids_groups_rows_by_content_id(self):
        user = _make_user()
        first_post = _make_post(user.id, "First")
        second_post = _make_post(user.id, "Second")
        db.session.commit()

        preference_profile_repository.replace_content_topic_assignments(
            domain="forum",
            content_type="post",
            content_id=first_post.id,
            topics=[
                {"topic_id": "battery-recycling", "confidence_score": 0.9},
                {"topic_id": "upcycling", "confidence_score": 0.4},
            ],
        )
        preference_profile_repository.replace_content_topic_assignments(
            domain="forum",
            content_type="post",
            content_id=second_post.id,
            topics=[{"topic_id": "composting", "confidence_score": 0.8}],
        )

        grouped = preference_profile_repository.list_content_topic_assignments_for_content_ids(
            domain="forum",
            content_type="post",
            content_ids=[first_post.id, second_post.id, 9999],
        )

        assert set(grouped) == {first_post.id, second_post.id}
        assert [row.topic_id for row in grouped[first_post.id]] == ["battery-recycling", "upcycling"]
        assert [row.topic_id for row in grouped[second_post.id]] == ["composting"]

    def test_list_recent_topic_exposure_counts_for_user_uses_recent_forum_snapshots(self):
        user = _make_user("exposure", "exposure@example.com")
        now = datetime.now(timezone.utc)

        behavior_event_repository.create_behavior_event(
            user_id=user.id,
            domain="forum",
            action_type="view",
            target_type="post",
            target_id=101,
            topic_payload=[{"topic_id": "old-topic", "confidence_score": 1.0}],
            created_at=now - timedelta(days=10),
        )
        behavior_event_repository.create_behavior_event(
            user_id=user.id,
            domain="forum",
            action_type="long_view",
            target_type="post",
            target_id=102,
            topic_payload=[
                {"topic_id": "battery-recycling", "confidence_score": 0.9},
                {"topic_id": "upcycling", "confidence_score": 0.4},
            ],
            created_at=now - timedelta(days=1),
        )
        behavior_event_repository.create_behavior_event(
            user_id=user.id,
            domain="forum",
            action_type="like",
            target_type="post",
            target_id=103,
            topic_payload=[{"topic_id": "battery-recycling", "confidence_score": 1.0}],
            created_at=now,
        )

        counts = behavior_event_repository.list_recent_topic_exposure_counts_for_user(
            user.id,
            domain="forum",
            limit=2,
        )

        assert counts == {
            "battery-recycling": 2,
            "upcycling": 1,
        }

    def test_list_published_posts_for_ranking_returns_candidate_window_in_recency_order(self):
        user = _make_user("window", "window@example.com")
        oldest = _make_post(user.id, "Oldest")
        middle = _make_post(user.id, "Middle")
        newest = _make_post(user.id, "Newest")
        forum_repository.soft_delete_post(middle)
        db.session.commit()

        posts = forum_repository.list_published_posts_for_ranking(candidate_limit=2)

        assert [post.id for post in posts] == [newest.id, oldest.id]
