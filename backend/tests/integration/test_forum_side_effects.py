"""What posting, reading, commenting and liking write besides the forum rows.

The service swallows errors from behaviour events and profiles, so the routes
answer 200 either way; and re-indexing runs as a job. These tests are what
notices when one of them stops happening.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.extensions.db import db
from app.models.forum import ForumPostChunk
from app.models.notification import Notification
from app.models.recommendation import ContentTopicAssignment, UserBehaviorEvent


@pytest.fixture(autouse=True)
def _keyword_topics(llm_unavailable):
    # Post topics come from keyword recall and then an LLM; with the provider
    # down the best keyword candidate is used, which keeps topics deterministic.
    return


def _events(user_id: int) -> list[tuple[str, str]]:
    rows = db.session.scalars(
        select(UserBehaviorEvent)
        .where(UserBehaviorEvent.user_id == user_id, UserBehaviorEvent.domain == "forum")
        .order_by(UserBehaviorEvent.id)
    )
    return [(e.action_type, e.target_type or "") for e in rows]


def _notifications(user_id: int) -> list[str]:
    rows = db.session.scalars(
        select(Notification.event_type)
        .where(Notification.recipient_user_id == user_id)
        .order_by(Notification.id)
    )
    return list(rows)


def _post(client, headers) -> int:
    response = client.post(
        "/api/forum/posts",
        json={"title": "Plastic bottle recycling", "content": "Rinse plastic bottles first."},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def test_posting_indexes_and_tags_the_post(app, client, make_auth_headers):
    _, author = make_auth_headers()

    post_id = _post(client, author)

    with app.app_context():
        chunks = db.session.scalars(
            select(ForumPostChunk).where(ForumPostChunk.post_id == post_id)
        ).all()
        topics = db.session.scalars(
            select(ContentTopicAssignment.topic_id).where(
                ContentTopicAssignment.content_type == "post",
                ContentTopicAssignment.content_id == post_id,
            )
        ).all()
        assert chunks
        assert topics


def test_reading_is_recorded(app, client, make_auth_headers):
    _, author = make_auth_headers()
    reader_id, reader = make_auth_headers()
    post_id = _post(client, author)

    client.get(f"/api/forum/posts/{post_id}", headers=reader)
    client.post(f"/api/forum/posts/{post_id}/long-view", headers=reader)

    with app.app_context():
        assert _events(reader_id) == [("view", "post"), ("long_view", "post")]


def test_comments_and_likes_are_recorded_and_notified(app, client, make_auth_headers):
    author_id, author = make_auth_headers()
    reader_id, reader = make_auth_headers()
    post_id = _post(client, author)

    comment = client.post(
        f"/api/forum/posts/{post_id}/comments", json={"content": "Thanks!"}, headers=reader
    ).json()["data"]
    client.post(
        f"/api/forum/posts/{post_id}/comments",
        json={"content": "You're welcome.", "parent_comment_id": comment["id"]},
        headers=author,
    )
    client.post(
        "/api/forum/likes", json={"target_type": "post", "target_id": post_id}, headers=reader
    )
    client.post(
        "/api/forum/likes",
        json={"target_type": "comment", "target_id": comment["id"]},
        headers=author,
    )

    with app.app_context():
        assert _events(reader_id) == [("comment_or_reply", "post"), ("like", "post")]
        assert _notifications(author_id) == ["post_commented", "post_liked"]
        assert _notifications(reader_id) == ["comment_replied", "comment_liked"]
