"""The forum lists run a fixed number of SQL statements, however many rows
they return or rank (PERFORMANCE_ISSUES #12)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from sqlalchemy import event

from app.models.forum import ForumComment, ForumPost, Like
from app.models.recommendation import ContentTopicAssignment, UserPreferenceProfile
from tests.support.database import db

TOPIC = "plastic_recycling"


@contextmanager
def _count_statements(connection) -> Iterator[list[str]]:
    statements: list[str] = []

    def record(_conn, _cursor, statement, *_args):
        if not statement.lstrip().upper().startswith(("SAVEPOINT", "RELEASE", "ROLLBACK")):
            statements.append(statement)

    event.listen(connection, "before_cursor_execute", record)
    try:
        yield statements
    finally:
        event.remove(connection, "before_cursor_execute", record)


def _seed_posts(author_id: int, liker_id: int, count: int) -> list[int]:
    post_ids = []
    for n in range(count):
        post = ForumPost(author_id=author_id, title=f"Post {n}", content="Rinse it.")
        db.session.add(post)
        db.session.flush()
        db.session.add(
            ContentTopicAssignment(
                domain="forum",
                content_type="post",
                content_id=post.id,
                topic_id=TOPIC,
                confidence_score=0.9,
                source="test",
            )
        )
        db.session.add(Like(user_id=liker_id, target_type="post", target_id=post.id))
        db.session.add(ForumComment(post_id=post.id, user_id=liker_id, content="Yes."))
        post_ids.append(post.id)
    db.session.commit()
    return post_ids


def _seed_comments(post_id: int, user_ids: list[int]) -> None:
    for user_id in user_ids:
        comment = ForumComment(post_id=post_id, user_id=user_id, content="Agreed.")
        db.session.add(comment)
        db.session.flush()
        db.session.add(Like(user_id=user_ids[0], target_type="comment", target_id=comment.id))
    db.session.commit()


def _give_history(user_id: int) -> None:
    # Enough events on one topic for ranking to leave the cold-start path.
    db.session.add(
        UserPreferenceProfile(
            user_id=user_id,
            profile_type="content_interest",
            profile_key=TOPIC,
            raw_score=3.0,
            normalized_score=0.9,
            confidence_score=0.9,
            event_count=5,
        )
    )
    db.session.commit()


def _statements_for(client, connection, url: str, headers=None) -> int:
    with _count_statements(connection) as statements:
        response = client.get(url, headers=headers or {})
    assert response.status_code == 200, response.text
    return len(statements)


@pytest.mark.parametrize("viewer", ["anonymous", "cold_start", "with_history"])
def test_post_list_does_not_grow_with_posts(client, db_connection, make_auth_headers, viewer):
    author_id, _ = make_auth_headers()
    viewer_id, viewer_headers = make_auth_headers()
    headers = None if viewer == "anonymous" else viewer_headers
    if viewer == "with_history":
        _give_history(viewer_id)

    _seed_posts(author_id, viewer_id, 5)
    few = _statements_for(client, db_connection, "/api/forum/posts", headers)
    _seed_posts(author_id, viewer_id, 15)
    many = _statements_for(client, db_connection, "/api/forum/posts", headers)

    assert many == few, f"{few} statements for 5 posts, {many} for 20"


@pytest.mark.parametrize("viewer", ["anonymous", "logged_in"])
def test_comment_list_does_not_grow_with_comments(client, db_connection, make_auth_headers, viewer):
    author_id, author_headers = make_auth_headers()
    commenter_ids = [make_auth_headers()[0] for _ in range(4)]
    headers = None if viewer == "anonymous" else author_headers
    [post_id] = _seed_posts(author_id, author_id, 1)
    url = f"/api/forum/posts/{post_id}/comments"

    _seed_comments(post_id, commenter_ids[:1])
    few = _statements_for(client, db_connection, url, headers)
    _seed_comments(post_id, commenter_ids)
    many = _statements_for(client, db_connection, url, headers)

    assert many == few, f"{few} statements for 2 comments, {many} for 6"
