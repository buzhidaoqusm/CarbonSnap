"""Logged-in lists rank a bounded set of candidates, however many rows exist,
and page on past them in plain SQL order (PERFORMANCE_ISSUES #13)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.extensions.db import db
from app.models.forum import ForumPost
from app.models.market import MarketItem, Order
from app.models.project import Project
from app.services.forum import forum_service
from app.services.market import market_service
from app.services.project import project_service

LIMIT = 5
PER_PAGE = 4


@pytest.fixture
def ranked_sizes(monkeypatch):
    """Cap the candidates at LIMIT and record how many each ranking gets."""
    sizes: list[int] = []

    def spy(module, name, keyword):
        original = getattr(module, name)

        def wrapper(session, **kwargs):
            sizes.append(len(kwargs[keyword]))
            return original(session, **kwargs)

        monkeypatch.setattr(module, name, wrapper)

    for module in (forum_service, project_service, market_service):
        monkeypatch.setattr(module, "RANKING_CANDIDATE_LIMIT", LIMIT, raising=False)
    spy(forum_service, "rank_posts_for_user", "posts")
    spy(project_service, "rank_projects_for_user", "projects")
    spy(market_service, "rank_items_for_user", "items")
    return sizes


def _ages(count: int) -> list[datetime]:
    now = datetime.now(UTC)
    return [now - timedelta(hours=n) for n in range(count)]


def _walk_pages(client, url: str, headers) -> tuple[list[int], int]:
    ids: list[int] = []
    totals = set()
    page = 1
    while True:
        response = client.get(f"{url}?page={page}&per_page={PER_PAGE}", headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        totals.add(data["total"])
        if not data["items"]:
            break
        ids += [item["id"] for item in data["items"]]
        page += 1
    assert len(totals) == 1, f"total changed between pages: {totals}"
    return ids, totals.pop()


def test_forum_ranks_a_bounded_set_and_pages_past_it(app, client, make_auth_headers, ranked_sizes):
    author_id, _ = make_auth_headers()
    _, viewer_headers = make_auth_headers()
    with app.app_context():
        posts = [
            ForumPost(author_id=author_id, title=f"Post {n}", content="Rinse it.", created_at=at)
            for n, at in enumerate(_ages(12))
        ]
        db.session.add_all(posts)
        db.session.commit()
        expected = {post.id for post in posts}

    ids, total = _walk_pages(client, "/api/forum/posts", viewer_headers)

    assert ranked_sizes and max(ranked_sizes) <= LIMIT
    assert total == 12
    assert len(ids) == len(set(ids)) and set(ids) == expected


def test_projects_rank_a_bounded_set_and_page_past_it(app, client, make_auth_headers, ranked_sizes):
    creator_id, _ = make_auth_headers()
    viewer_id, viewer_headers = make_auth_headers()
    deadline = datetime.now(UTC) + timedelta(days=30)
    with app.app_context():
        own = Project(
            creator_user_id=viewer_id, title="Mine", points_target=100, deadline_at=deadline
        )
        others = [
            Project(
                creator_user_id=creator_id,
                title=f"Project {n}",
                points_target=100,
                deadline_at=deadline + timedelta(days=n),
                created_at=at,
            )
            for n, at in enumerate(_ages(12))
        ]
        db.session.add_all([own, *others])
        db.session.commit()
        own_id = own.id
        expected = {own.id} | {project.id for project in others}

    ids, total = _walk_pages(client, "/api/projects", viewer_headers)

    assert ranked_sizes and max(ranked_sizes) <= LIMIT
    assert total == 13
    assert ids[0] == own_id
    assert len(ids) == len(set(ids)) and set(ids) == expected


def test_market_ranks_a_bounded_set_and_pages_past_it(app, client, make_auth_headers, ranked_sizes):
    seller_id, _ = make_auth_headers()
    viewer_id, viewer_headers = make_auth_headers()
    with app.app_context():
        items = [
            MarketItem(seller_id=seller_id, title=f"Item {n}", price_points=10, created_at=at)
            for n, at in enumerate(_ages(12))
        ]
        db.session.add_all(items)
        db.session.flush()
        # Something the viewer already bought is left out, wherever it falls.
        bought = items[7]
        db.session.add(
            Order(item_id=bought.id, buyer_id=viewer_id, seller_id=seller_id, price_points=10)
        )
        db.session.commit()
        expected = {item.id for item in items} - {bought.id}

    ids, total = _walk_pages(client, "/api/market/items", viewer_headers)

    assert ranked_sizes and max(ranked_sizes) <= LIMIT
    assert total == 11
    assert len(ids) == len(set(ids)) and set(ids) == expected
