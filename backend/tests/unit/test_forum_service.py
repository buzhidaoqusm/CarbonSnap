"""Unit tests for services/forum/forum_service.py.

Strategy: call service functions directly (no HTTP layer).
The db_session fixture (autouse=True in conftest.py) provides a clean
database for every test — no need to wrap calls in app.app_context().
"""

import pytest
from werkzeug.security import generate_password_hash

from app.extensions.db import db
from app.models.user import User
from app.services.forum import forum_service
from app.services.forum.forum_service import ForumError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(username="alice", email="alice@example.com", avatar_url=None):
    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash("pw"),
        avatar_url=avatar_url,
    )
    db.session.add(user)
    db.session.flush()
    return user


# ---------------------------------------------------------------------------
# Post CRUD
# ---------------------------------------------------------------------------

class TestCreatePost:
    def test_creates_post_and_returns_dict(self):
        user = _make_user()
        result = forum_service.create_post(
            author_id=user.id, title="Hello", content="World"
        )
        assert result["title"] == "Hello"
        assert result["content"] == "World"
        assert result["author_id"] == user.id
        assert result["like_count"] == 0
        assert result["liked_by_user"] is False

    def test_post_id_is_positive_integer(self):
        user = _make_user()
        result = forum_service.create_post(author_id=user.id, title="T", content="C")
        assert isinstance(result["id"], int)
        assert result["id"] > 0

    def test_create_post_queues_forum_maintenance(self, monkeypatch):
        user = _make_user("indexer", "indexer@example.com")
        captured = {}

        monkeypatch.setattr(
            forum_service.forum_background_job_service,
            "enqueue_post_refresh",
            lambda **kwargs: captured.update(kwargs) or None,
        )

        forum_service.create_post(author_id=user.id, title="Bottle", content="Tips")

        assert captured == {
            "post_id": 1,
            "title": "Bottle",
            "content": "Tips",
        }


class TestGetPost:
    def test_get_existing_post(self):
        user = _make_user()
        created = forum_service.create_post(author_id=user.id, title="T", content="C")
        fetched = forum_service.get_post(created["id"])
        assert fetched["id"] == created["id"]

    def test_get_nonexistent_post_raises(self):
        with pytest.raises(ForumError) as exc_info:
            forum_service.get_post(99999)
        assert exc_info.value.http_status == 404

    def test_liked_by_user_field_present_when_viewer_given(self):
        user = _make_user()
        created = forum_service.create_post(author_id=user.id, title="T", content="C")
        result = forum_service.get_post(created["id"], viewer_user_id=user.id)
        assert result["liked_by_user"] is False


class TestRecordPostLongView:
    def test_records_long_view_and_recomputes_profile(self, monkeypatch):
        user = _make_user("reader", "reader@example.com")
        created = forum_service.create_post(author_id=user.id, title="Battery", content="Tips")
        captured = {}
        recomputed = []

        monkeypatch.setattr(
            forum_service.behavior_event_repository,
            "get_latest_behavior_event_for_target",
            lambda *args, **kwargs: None,
        )
        monkeypatch.setattr(
            forum_service.behavior_event_service,
            "record_forum_long_view",
            lambda **kwargs: captured.update(kwargs) or object(),
        )
        monkeypatch.setattr(
            forum_service.preference_profile_service,
            "recompute_user_preference_profiles",
            lambda user_id: recomputed.append(user_id),
        )

        result = forum_service.record_post_long_view(created["id"], viewer_user_id=user.id)

        assert result == {"tracked": True}
        assert captured == {"user_id": user.id, "post_id": created["id"]}
        assert recomputed == [user.id]

    def test_skips_duplicate_long_view_inside_dedup_window(self, monkeypatch):
        user = _make_user("dedup", "dedup@example.com")
        created = forum_service.create_post(author_id=user.id, title="Plastic", content="Bottle")
        latest_event = type(
            "Event",
            (),
            {"created_at": forum_service._utc_now() - forum_service.FORUM_LONG_VIEW_DEDUP_WINDOW / 2},
        )()

        monkeypatch.setattr(
            forum_service.behavior_event_repository,
            "get_latest_behavior_event_for_target",
            lambda *args, **kwargs: latest_event,
        )
        monkeypatch.setattr(
            forum_service.behavior_event_service,
            "record_forum_long_view",
            lambda **kwargs: pytest.fail("should not record duplicate long-view"),
        )

        result = forum_service.record_post_long_view(created["id"], viewer_user_id=user.id)

        assert result == {"tracked": False, "reason": "deduplicated"}

    def test_skips_duplicate_long_view_when_latest_timestamp_is_naive(self, monkeypatch):
        user = _make_user("naive", "naive@example.com")
        created = forum_service.create_post(author_id=user.id, title="Glass", content="Bottle")
        latest_event = type(
            "Event",
            (),
            {
                "created_at": (
                    forum_service._utc_now() - forum_service.FORUM_LONG_VIEW_DEDUP_WINDOW / 2
                ).replace(tzinfo=None)
            },
        )()

        monkeypatch.setattr(
            forum_service.behavior_event_repository,
            "get_latest_behavior_event_for_target",
            lambda *args, **kwargs: latest_event,
        )
        monkeypatch.setattr(
            forum_service.behavior_event_service,
            "record_forum_long_view",
            lambda **kwargs: pytest.fail("should not record duplicate long-view for naive timestamps"),
        )

        result = forum_service.record_post_long_view(created["id"], viewer_user_id=user.id)

        assert result == {"tracked": False, "reason": "deduplicated"}

    def test_record_post_long_view_returns_tracked_payload(self):
        user = _make_user("reader", "reader@example.com")
        created = forum_service.create_post(author_id=user.id, title="Read", content="This is detailed")

        result = forum_service.record_post_long_view(created["id"], viewer_user_id=user.id)

        assert result == {"tracked": True}

    def test_record_post_long_view_for_missing_post_raises(self):
        user = _make_user("missing", "missing@example.com")

        with pytest.raises(ForumError) as exc_info:
            forum_service.record_post_long_view(99999, viewer_user_id=user.id)

        assert exc_info.value.http_status == 404


class TestUpdatePost:
    def test_author_can_update(self):
        user = _make_user()
        post = forum_service.create_post(author_id=user.id, title="Old", content="Old")
        updated = forum_service.update_post(
            post["id"], operator_user_id=user.id, title="New", content="New content"
        )
        assert updated["title"] == "New"
        assert updated["content"] == "New content"

    def test_non_author_cannot_update(self):
        author = _make_user("author", "author@x.com")
        other = _make_user("other", "other@x.com")
        post = forum_service.create_post(author_id=author.id, title="T", content="C")
        with pytest.raises(ForumError) as exc_info:
            forum_service.update_post(post["id"], operator_user_id=other.id, title="X")
        assert exc_info.value.http_status == 403

    def test_update_post_queues_forum_maintenance(self, monkeypatch):
        user = _make_user("editor", "editor@example.com")
        post = forum_service.create_post(author_id=user.id, title="Old", content="Old")
        captured = {}

        monkeypatch.setattr(
            forum_service.forum_background_job_service,
            "enqueue_post_refresh",
            lambda **kwargs: captured.update(kwargs) or None,
        )

        forum_service.update_post(post["id"], operator_user_id=user.id, title="New", content="Fresh")

        assert captured == {
            "post_id": post["id"],
            "title": "New",
            "content": "Fresh",
        }


class TestDeletePost:
    def test_author_can_delete(self):
        user = _make_user()
        post = forum_service.create_post(author_id=user.id, title="T", content="C")
        forum_service.delete_post(post["id"], operator_user_id=user.id)
        with pytest.raises(ForumError) as exc_info:
            forum_service.get_post(post["id"])
        assert exc_info.value.http_status == 404

    def test_non_author_cannot_delete(self):
        author = _make_user("a", "a@x.com")
        other = _make_user("b", "b@x.com")
        post = forum_service.create_post(author_id=author.id, title="T", content="C")
        with pytest.raises(ForumError) as exc_info:
            forum_service.delete_post(post["id"], operator_user_id=other.id)
        assert exc_info.value.http_status == 403

    def test_delete_post_removes_forum_index(self, monkeypatch):
        user = _make_user("deleter", "deleter@example.com")
        post = forum_service.create_post(author_id=user.id, title="T", content="C")
        removed = []

        monkeypatch.setattr(
            forum_service.forum_background_job_service,
            "enqueue_post_removal",
            lambda post_id: removed.append(post_id) or None,
        )

        forum_service.delete_post(post["id"], operator_user_id=user.id)

        assert removed == [post["id"]]


class TestListPosts:
    def test_returns_pagination_envelope(self):
        user = _make_user()
        for i in range(3):
            forum_service.create_post(author_id=user.id, title=f"T{i}", content="C")
        result = forum_service.list_posts(page=1, per_page=2)
        assert result["total"] == 3
        assert len(result["items"]) == 2
        assert result["page"] == 1
        assert result["per_page"] == 2

    def test_deleted_posts_excluded(self):
        user = _make_user()
        p1 = forum_service.create_post(author_id=user.id, title="Keep", content="C")
        p2 = forum_service.create_post(author_id=user.id, title="Del", content="C")
        forum_service.delete_post(p2["id"], operator_user_id=user.id)
        result = forum_service.list_posts(page=1, per_page=10)
        ids = [item["id"] for item in result["items"]]
        assert p1["id"] in ids
        assert p2["id"] not in ids

    def test_authenticated_user_uses_personalized_order(self, monkeypatch):
        user = _make_user("personal", "personal@example.com")
        first = forum_service.create_post(author_id=user.id, title="Plastic", content="Bottle")
        second = forum_service.create_post(author_id=user.id, title="Battery", content="Cell")

        monkeypatch.setattr(
            forum_service,
            "rank_posts_for_user",
            lambda posts, user_id: list(reversed(posts)),
        )

        result = forum_service.list_posts(page=1, per_page=10, viewer_user_id=user.id)
        assert [item["id"] for item in result["items"]] == [first["id"], second["id"]]

    def test_authenticated_user_ranks_candidate_window_once_then_slices_globally(self, monkeypatch):
        user = _make_user("global", "global@example.com")
        created_posts = [
            forum_service.create_post(author_id=user.id, title=f"Post {index}", content="C")
            for index in range(1, 11)
        ]
        candidate_posts = forum_service.forum_repository.list_published_posts_for_ranking(candidate_limit=10)
        captured = {}

        monkeypatch.setattr(
            forum_service.forum_repository,
            "count_all_published_posts",
            lambda: 10,
        )

        def reverse_ranked_posts(*, posts, user_id):
            captured["posts"] = [post.id for post in posts]
            captured["user_id"] = user_id
            return list(reversed(posts))

        monkeypatch.setattr(
            forum_service,
            "rank_posts_for_user",
            reverse_ranked_posts,
        )

        result = forum_service.list_posts(page=2, per_page=3, viewer_user_id=user.id)

        assert captured == {
            "posts": [post.id for post in candidate_posts],
            "user_id": user.id,
        }
        assert [item["id"] for item in result["items"]] == [
            created_posts[3]["id"],
            created_posts[4]["id"],
            created_posts[5]["id"],
        ]
        assert result["total"] == 10

    def test_authenticated_user_total_comes_from_full_published_count_not_candidate_window(self, monkeypatch):
        user = _make_user("counted", "counted@example.com")
        for index in range(1, 8):
            forum_service.create_post(author_id=user.id, title=f"Post {index}", content="C")

        candidate_posts = forum_service.forum_repository.list_published_posts_for_ranking(candidate_limit=5)

        monkeypatch.setattr(
            forum_service.forum_repository,
            "list_published_posts_for_ranking",
            lambda *, candidate_limit: candidate_posts,
        )
        monkeypatch.setattr(
            forum_service.forum_repository,
            "count_all_published_posts",
            lambda: 7,
        )
        monkeypatch.setattr(
            forum_service,
            "rank_posts_for_user",
            lambda *, posts, user_id: posts,
        )

        result = forum_service.list_posts(page=1, per_page=5, viewer_user_id=user.id)

        assert len(result["items"]) == 5
        assert result["total"] == 7

# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

class TestCreateComment:
    def test_top_level_comment(self):
        user = _make_user()
        post = forum_service.create_post(author_id=user.id, title="T", content="C")
        comment = forum_service.create_comment(
            post_id=post["id"], user_id=user.id, content="Nice post!"
        )
        assert comment["post_id"] == post["id"]
        assert comment["parent_comment_id"] is None
        assert comment["like_count"] == 0

    def test_comment_includes_author_profile_fields(self):
        user = _make_user(
            username="comment_author",
            email="comment-author@example.com",
            avatar_url="/api/uploads/avatars/comment-author.svg",
        )
        post = forum_service.create_post(author_id=user.id, title="T", content="C")

        comment = forum_service.create_comment(
            post_id=post["id"], user_id=user.id, content="Nice post!"
        )

        assert comment["author_username"] == "comment_author"
        assert comment["author_avatar_url"] == "/api/uploads/avatars/comment-author.svg"

    def test_reply_to_comment(self):
        user = _make_user()
        post = forum_service.create_post(author_id=user.id, title="T", content="C")
        parent = forum_service.create_comment(
            post_id=post["id"], user_id=user.id, content="Parent"
        )
        reply = forum_service.create_comment(
            post_id=post["id"],
            user_id=user.id,
            content="Reply",
            parent_comment_id=parent["id"],
        )
        assert reply["parent_comment_id"] == parent["id"]

    def test_comment_on_nonexistent_post_raises(self):
        user = _make_user()
        with pytest.raises(ForumError) as exc_info:
            forum_service.create_comment(post_id=99999, user_id=user.id, content="X")
        assert exc_info.value.http_status == 404

    def test_reply_to_nonexistent_comment_raises(self):
        user = _make_user()
        post = forum_service.create_post(author_id=user.id, title="T", content="C")
        with pytest.raises(ForumError) as exc_info:
            forum_service.create_comment(
                post_id=post["id"], user_id=user.id, content="X", parent_comment_id=99999
            )
        assert exc_info.value.http_status == 404


class TestDeleteComment:
    def test_author_can_delete_comment(self):
        user = _make_user()
        post = forum_service.create_post(author_id=user.id, title="T", content="C")
        comment = forum_service.create_comment(
            post_id=post["id"], user_id=user.id, content="Bye"
        )
        forum_service.delete_comment(comment["id"], operator_user_id=user.id)
        result = forum_service.list_comments(post["id"])
        ids = [c["id"] for c in result["items"]]
        assert comment["id"] not in ids

    def test_non_author_cannot_delete_comment(self):
        author = _make_user("a", "a@x.com")
        other = _make_user("b", "b@x.com")
        post = forum_service.create_post(author_id=author.id, title="T", content="C")
        comment = forum_service.create_comment(
            post_id=post["id"], user_id=author.id, content="Mine"
        )
        with pytest.raises(ForumError) as exc_info:
            forum_service.delete_comment(comment["id"], operator_user_id=other.id)
        assert exc_info.value.http_status == 403


# ---------------------------------------------------------------------------
# Likes
# ---------------------------------------------------------------------------

class TestToggleLike:
    def test_like_post(self):
        user = _make_user()
        post = forum_service.create_post(author_id=user.id, title="T", content="C")
        result = forum_service.toggle_like(
            user_id=user.id, target_type="post", target_id=post["id"]
        )
        assert result["liked"] is True
        assert result["like_count"] == 1

    def test_unlike_post(self):
        user = _make_user()
        post = forum_service.create_post(author_id=user.id, title="T", content="C")
        forum_service.toggle_like(user_id=user.id, target_type="post", target_id=post["id"])
        result = forum_service.toggle_like(
            user_id=user.id, target_type="post", target_id=post["id"]
        )
        assert result["liked"] is False
        assert result["like_count"] == 0

    def test_unlike_records_unlike_behavior_and_recomputes_profile(self, monkeypatch):
        user = _make_user("toggle", "toggle@x.com")
        post = forum_service.create_post(author_id=user.id, title="T", content="C")
        forum_service.toggle_like(user_id=user.id, target_type="post", target_id=post["id"])

        captured = {}
        recomputed = []

        monkeypatch.setattr(
            forum_service.behavior_event_service,
            "record_forum_unlike",
            lambda **kwargs: captured.update(kwargs) or object(),
        )
        monkeypatch.setattr(
            forum_service.preference_profile_service,
            "recompute_user_preference_profiles",
            lambda user_id: recomputed.append(user_id),
        )

        result = forum_service.toggle_like(user_id=user.id, target_type="post", target_id=post["id"])

        assert result["liked"] is False
        assert captured == {
            "user_id": user.id,
            "target_type": "post",
            "target_id": post["id"],
        }
        assert recomputed == [user.id]

    def test_like_comment(self):
        user = _make_user()
        post = forum_service.create_post(author_id=user.id, title="T", content="C")
        comment = forum_service.create_comment(
            post_id=post["id"], user_id=user.id, content="Hi"
        )
        result = forum_service.toggle_like(
            user_id=user.id, target_type="comment", target_id=comment["id"]
        )
        assert result["liked"] is True

    def test_invalid_target_type_raises(self):
        user = _make_user()
        with pytest.raises(ForumError):
            forum_service.toggle_like(user_id=user.id, target_type="invalid", target_id=1)

    def test_like_nonexistent_post_raises(self):
        user = _make_user()
        with pytest.raises(ForumError) as exc_info:
            forum_service.toggle_like(user_id=user.id, target_type="post", target_id=99999)
        assert exc_info.value.http_status == 404

    def test_multiple_users_like_same_post(self):
        u1 = _make_user("u1", "u1@x.com")
        u2 = _make_user("u2", "u2@x.com")
        post = forum_service.create_post(author_id=u1.id, title="T", content="C")
        forum_service.toggle_like(user_id=u1.id, target_type="post", target_id=post["id"])
        result = forum_service.toggle_like(
            user_id=u2.id, target_type="post", target_id=post["id"]
        )
        assert result["like_count"] == 2
