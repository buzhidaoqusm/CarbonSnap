"""
Export persisted content_topic_assignments into repeatable seed JSON files.

Usage (from repo root, with backend venv available):
  backend\\.venv\\Scripts\\python.exe backend\\scripts\\export_content_topic_assignments_to_seed.py --replace-existing
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND_ROOT.parent
sys.path.insert(0, str(_BACKEND_ROOT))

from app import create_app
from app.extensions.db import db
from app.models.forum import ForumPost
from app.models.market import MarketItem
from app.models.project import Project
from app.models.recommendation import ContentTopicAssignment
from app.models.user import User

SEEDS_ROOT = _REPO_ROOT / "data" / "seeds"
FORUM_POST_SEEDS_ROOT = SEEDS_ROOT / "forum_posts"
MARKET_ITEM_SEEDS_ROOT = SEEDS_ROOT / "market_items"
PROJECT_SEEDS_ROOT = SEEDS_ROOT / "projects"
TOPIC_ASSIGNMENT_SEEDS_ROOT = SEEDS_ROOT / "content_topic_assignments"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export content topic assignments into seed files."
    )
    parser.add_argument("--replace-existing", action="store_true")
    return parser.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _normalize_list(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value)


def _normalize_json_text(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    try:
        parsed = json.loads(value)
    except Exception:
        return ()
    return _normalize_list(parsed)


def _normalize_datetime_signature(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.isoformat(sep=" ")
        return value.astimezone(UTC).replace(tzinfo=None).isoformat(sep=" ")
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.isoformat(sep=" ")
        return parsed.astimezone(UTC).replace(tzinfo=None).isoformat(sep=" ")
    return str(value)


def _load_user_seed_key_by_identity() -> dict[tuple[str, str], str]:
    mapping: dict[tuple[str, str], str] = {}
    for seed_path in sorted((SEEDS_ROOT / "users").glob("*.json")):
        if seed_path.name == "template.json":
            continue
        payload = _load_json(seed_path)
        username = str(payload.get("username") or "").strip()
        email = str(payload.get("email") or "").strip()
        seed_key = str(payload.get("_seed_key") or "").strip()
        if username and email and seed_key:
            mapping[(username, email)] = seed_key
    return mapping


def _build_forum_seed_lookup(
    user_seed_keys: dict[tuple[str, str], str],
) -> dict[tuple[str, str, str, tuple[str, ...], str], str]:
    lookup: dict[tuple[str, str, str, tuple[str, ...], str], str] = {}
    for seed_path in sorted(FORUM_POST_SEEDS_ROOT.glob("*.json")):
        if seed_path.name == "template.json":
            continue
        payload = _load_json(seed_path)
        seed_key = str(payload.get("_seed_key") or "").strip()
        signature = (
            str(payload.get("author_ref") or "").strip(),
            str(payload.get("title") or ""),
            str(payload.get("content") or ""),
            _normalize_list(payload.get("image_urls_json")),
            str(payload.get("status") or ""),
        )
        lookup[signature] = seed_key
    return lookup


def _build_market_seed_lookup() -> dict[tuple[str, str, str, tuple[str, ...], int, str], str]:
    lookup: dict[tuple[str, str, str, tuple[str, ...], int, str], str] = {}
    for seed_path in sorted(MARKET_ITEM_SEEDS_ROOT.glob("*.json")):
        if seed_path.name == "template.json":
            continue
        payload = _load_json(seed_path)
        seed_key = str(payload.get("_seed_key") or "").strip()
        signature = (
            str(payload.get("seller_ref") or "").strip(),
            str(payload.get("title") or ""),
            str(payload.get("description") or ""),
            _normalize_list(payload.get("image_urls_json")),
            int(payload.get("price_points") or 0),
            str(payload.get("status") or ""),
        )
        lookup[signature] = seed_key
    return lookup


def _build_project_seed_lookup() -> dict[
    tuple[str, str, str, str | None, int, int, str, str | None], str
]:
    lookup: dict[tuple[str, str, str, str | None, int, int, str, str | None], str] = {}
    for seed_path in sorted(PROJECT_SEEDS_ROOT.glob("*.json")):
        if seed_path.name == "template.json":
            continue
        payload = _load_json(seed_path)
        seed_key = str(payload.get("_seed_key") or "").strip()
        signature = (
            str(payload.get("creator_user_ref") or "").strip(),
            str(payload.get("title") or ""),
            str(payload.get("description") or ""),
            payload.get("cover_image_url"),
            int(payload.get("points_target") or 0),
            int(payload.get("points_raised") or 0),
            str(payload.get("status") or ""),
            _normalize_datetime_signature(payload.get("deadline_at")),
        )
        lookup[signature] = seed_key
    return lookup


def _resolve_forum_post_seed_key(
    post: ForumPost,
    user_seed_keys: dict[tuple[str, str], str],
    lookup: dict[tuple[str, str, str, tuple[str, ...], str], str],
) -> str:
    author = db.session.get(User, post.author_id)
    if author is None:
        raise ValueError(f"Author {post.author_id} not found for forum post {post.id}.")
    author_seed_key = user_seed_keys.get((str(author.username), str(author.email)))
    if not author_seed_key:
        raise ValueError(
            f"Could not map forum post author {author.username}/{author.email} to a user seed."
        )
    signature = (
        f"users.{author_seed_key}",
        str(post.title or ""),
        str(post.content or ""),
        _normalize_json_text(post.image_urls_json),
        str(post.status or ""),
    )
    seed_key = lookup.get(signature)
    if not seed_key:
        raise ValueError(f"Could not map forum post {post.id} to an existing forum seed.")
    return seed_key


def _resolve_market_item_seed_key(
    item: MarketItem,
    user_seed_keys: dict[tuple[str, str], str],
    lookup: dict[tuple[str, str, str, tuple[str, ...], int, str], str],
) -> str:
    seller = db.session.get(User, item.seller_id)
    if seller is None:
        raise ValueError(f"Seller {item.seller_id} not found for market item {item.id}.")
    seller_seed_key = user_seed_keys.get((str(seller.username), str(seller.email)))
    if not seller_seed_key:
        raise ValueError(
            f"Could not map market item seller {seller.username}/{seller.email} to a user seed."
        )
    signature = (
        f"users.{seller_seed_key}",
        str(item.title or ""),
        str(item.description or ""),
        _normalize_json_text(item.image_urls_json),
        int(item.price_points or 0),
        str(item.status or ""),
    )
    seed_key = lookup.get(signature)
    if not seed_key:
        raise ValueError(f"Could not map market item {item.id} to an existing market seed.")
    return seed_key


def _resolve_project_seed_key(
    project: Project,
    user_seed_keys: dict[tuple[str, str], str],
    lookup: dict[tuple[str, str, str, str | None, int, int, str, str | None], str],
) -> str:
    creator = db.session.get(User, project.creator_user_id)
    if creator is None:
        raise ValueError(f"Creator {project.creator_user_id} not found for project {project.id}.")
    creator_seed_key = user_seed_keys.get((str(creator.username), str(creator.email)))
    if not creator_seed_key:
        raise ValueError(
            f"Could not map project creator {creator.username}/{creator.email} to a user seed."
        )
    signature = (
        f"users.{creator_seed_key}",
        str(project.title or ""),
        str(project.description or ""),
        project.cover_image_url,
        int(project.points_target or 0),
        int(project.points_raised or 0),
        str(project.status or ""),
        _normalize_datetime_signature(project.deadline_at),
    )
    seed_key = lookup.get(signature)
    if not seed_key:
        raise ValueError(f"Could not map project {project.id} to an existing project seed.")
    return seed_key


def _remove_existing_assignment_seed_files() -> None:
    TOPIC_ASSIGNMENT_SEEDS_ROOT.mkdir(parents=True, exist_ok=True)
    for seed_path in TOPIC_ASSIGNMENT_SEEDS_ROOT.glob("*.json"):
        if seed_path.name == "template.json":
            continue
        seed_path.unlink()


def main() -> None:
    args = _parse_args()
    app = create_app()

    with app.app_context():
        if args.replace_existing:
            _remove_existing_assignment_seed_files()

        user_seed_keys = _load_user_seed_key_by_identity()
        forum_lookup = _build_forum_seed_lookup(user_seed_keys)
        market_lookup = _build_market_seed_lookup()
        project_lookup = _build_project_seed_lookup()

        forum_seed_keys = {
            post.id: _resolve_forum_post_seed_key(post, user_seed_keys, forum_lookup)
            for post in db.session.scalars(select(ForumPost).order_by(ForumPost.id.asc()))
        }
        market_seed_keys = {
            item.id: _resolve_market_item_seed_key(item, user_seed_keys, market_lookup)
            for item in db.session.scalars(select(MarketItem).order_by(MarketItem.id.asc()))
        }
        project_seed_keys = {
            project.id: _resolve_project_seed_key(project, user_seed_keys, project_lookup)
            for project in db.session.scalars(select(Project).order_by(Project.id.asc()))
        }

        assignments = list(
            db.session.scalars(
                select(ContentTopicAssignment).order_by(
                    ContentTopicAssignment.domain.asc(),
                    ContentTopicAssignment.content_type.asc(),
                    ContentTopicAssignment.content_id.asc(),
                    ContentTopicAssignment.confidence_score.desc(),
                    ContentTopicAssignment.id.asc(),
                )
            )
        )

        exported = 0
        for assignment in assignments:
            domain = str(assignment.domain or "").strip().lower()
            content_type = str(assignment.content_type or "").strip().lower()

            if domain == "forum" and content_type == "post":
                seed_key = forum_seed_keys.get(int(assignment.content_id))
                content_ref = f"forum_posts.{seed_key}" if seed_key else None
            elif domain == "market" and content_type == "item":
                seed_key = market_seed_keys.get(int(assignment.content_id))
                content_ref = f"market_items.{seed_key}" if seed_key else None
            elif domain == "project" and content_type == "project":
                seed_key = project_seed_keys.get(int(assignment.content_id))
                content_ref = f"projects.{seed_key}" if seed_key else None
            else:
                raise ValueError(
                    f"Unsupported content topic assignment target: domain={domain!r} content_type={content_type!r}"
                )

            if not content_ref or not seed_key:
                raise ValueError(
                    f"Could not resolve content_topic_assignment {assignment.id} to an existing seed target."
                )

            assignment_seed_key = f"{domain}-{seed_key}-{assignment.topic_id}"
            payload = {
                "_seed_key": assignment_seed_key,
                "domain": domain,
                "content_type": content_type,
                "content_ref": content_ref,
                "topic_id": assignment.topic_id,
                "confidence_score": assignment.confidence_score,
                "source": assignment.source,
                "created_at": assignment.created_at.isoformat() if assignment.created_at else None,
                "updated_at": assignment.updated_at.isoformat() if assignment.updated_at else None,
            }
            _write_json(TOPIC_ASSIGNMENT_SEEDS_ROOT / f"{assignment_seed_key}.json", payload)
            exported += 1

        print("Content topic assignment seed export complete.")
        print(f"- assignments exported: {exported}")


if __name__ == "__main__":
    main()
