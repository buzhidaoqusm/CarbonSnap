"""
Export persisted forum RAG chunks and FAISS assets into repeatable seed files.

Usage (from repo root, with backend venv available):
  backend\\.venv\\Scripts\\python.exe backend\\scripts\\export_forum_rag_to_seed.py --replace-existing
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import select

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND_ROOT.parent
sys.path.insert(0, str(_BACKEND_ROOT))

from app import create_app
from app.extensions.db import db
from app.models.forum import ForumPost, ForumPostChunk
from app.models.user import User

SEEDS_ROOT = _REPO_ROOT / "data" / "seeds"
FORUM_POST_SEEDS_ROOT = SEEDS_ROOT / "forum_posts"
FORUM_POST_CHUNK_SEEDS_ROOT = SEEDS_ROOT / "forum_post_chunks"
SEED_FAISS_ASSETS_ROOT = SEEDS_ROOT / "assets" / "faiss"
FAISS_ROOT = _REPO_ROOT / "data" / "faiss"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export forum RAG chunks and FAISS assets into seed files."
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


def _load_user_seed_key_by_identity() -> dict[tuple[str, str], str]:
    mapping: dict[tuple[str, str], str] = {}
    users_root = SEEDS_ROOT / "users"
    for seed_path in sorted(users_root.glob("*.json")):
        if seed_path.name == "template.json":
            continue
        payload = _load_json(seed_path)
        username = str(payload.get("username") or "").strip()
        email = str(payload.get("email") or "").strip()
        seed_key = str(payload.get("_seed_key") or "").strip()
        if username and email and seed_key:
            mapping[(username, email)] = seed_key
    return mapping


def _build_forum_post_seed_signature_index(
    user_seed_keys: dict[tuple[str, str], str],
) -> dict[tuple[str, str, str, tuple[str, ...], str], str]:
    signatures: dict[tuple[str, str, str, tuple[str, ...], str], str] = {}
    for seed_path in sorted(FORUM_POST_SEEDS_ROOT.glob("*.json")):
        if seed_path.name == "template.json":
            continue
        payload = _load_json(seed_path)
        seed_key = str(payload.get("_seed_key") or "").strip()
        author_ref = str(payload.get("author_ref") or "").strip()
        title = str(payload.get("title") or "")
        content = str(payload.get("content") or "")
        status = str(payload.get("status") or "")
        image_urls = _normalize_list(payload.get("image_urls_json"))
        signature = (author_ref, title, content, image_urls, status)
        if signature in signatures:
            raise ValueError(f"Duplicate forum post seed signature detected for {seed_key}.")
        signatures[signature] = seed_key
    return signatures


def _load_forum_post_seed_keys_in_load_order() -> list[str]:
    seed_keys: list[str] = []
    for seed_path in sorted(FORUM_POST_SEEDS_ROOT.glob("*.json")):
        if seed_path.name == "template.json":
            continue
        payload = _load_json(seed_path)
        seed_key = str(payload.get("_seed_key") or "").strip()
        if seed_key:
            seed_keys.append(seed_key)
    return seed_keys


def _resolve_post_seed_key(
    *,
    post: ForumPost,
    user_seed_keys: dict[tuple[str, str], str],
    post_signatures: dict[tuple[str, str, str, tuple[str, ...], str], str],
) -> str:
    user = db.session.get(User, post.author_id)
    if user is None:
        raise ValueError(f"Author {post.author_id} not found for forum post {post.id}.")

    author_seed_key = user_seed_keys.get((str(user.username), str(user.email)))
    if not author_seed_key:
        raise ValueError(
            f"Could not map forum post author {user.username}/{user.email} to an existing user seed key."
        )

    image_urls = _normalize_list(json.loads(post.image_urls_json) if post.image_urls_json else None)
    signature = (
        f"users.{author_seed_key}",
        str(post.title or ""),
        str(post.content or ""),
        image_urls,
        str(post.status or ""),
    )
    seed_key = post_signatures.get(signature)
    if not seed_key:
        raise ValueError(
            f"Could not map forum post {post.id} ({post.title!r}) to an existing forum post seed."
        )
    return seed_key


def _remove_existing_chunk_seed_files() -> None:
    FORUM_POST_CHUNK_SEEDS_ROOT.mkdir(parents=True, exist_ok=True)
    for seed_path in FORUM_POST_CHUNK_SEEDS_ROOT.glob("*.json"):
        if seed_path.name == "template.json":
            continue
        seed_path.unlink()


def _export_faiss_assets() -> int:
    if SEED_FAISS_ASSETS_ROOT.exists():
        shutil.rmtree(SEED_FAISS_ASSETS_ROOT)
    SEED_FAISS_ASSETS_ROOT.mkdir(parents=True, exist_ok=True)

    exported = 0
    if not FAISS_ROOT.exists():
        return exported

    for source_path in FAISS_ROOT.rglob("*"):
        if not source_path.is_file() or source_path.name == ".gitkeep":
            continue
        relative_path = source_path.relative_to(FAISS_ROOT)
        target_path = SEED_FAISS_ASSETS_ROOT / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        exported += 1
    return exported


def _load_manifest_chunk_rows() -> list[dict[str, Any]]:
    manifest_path = FAISS_ROOT / "forum_rag.json"
    if not manifest_path.is_file():
        return []

    payload = _load_json(manifest_path)
    raw_records = payload.get("records")
    if not isinstance(raw_records, list):
        return []

    normalized_rows: list[dict[str, Any]] = []
    for item in raw_records:
        if not isinstance(item, dict):
            continue
        chunk_id = str(item.get("chunk_id") or "").strip()
        if not chunk_id:
            continue
        normalized_rows.append(
            {
                "post_id": int(item.get("post_id")),
                "chunk_text": str(item.get("chunk_text") or ""),
                "chunk_index": int(item.get("chunk_index") or 0),
                "section_title": item.get("section_title"),
                "chunk_version": int(item.get("chunk_version") or 1),
                "embedding_id": chunk_id,
                "numeric_id": int(item.get("numeric_id") or 0),
            }
        )
    normalized_rows.sort(
        key=lambda row: (
            row["post_id"],
            row["chunk_version"],
            row["chunk_index"],
            row["numeric_id"],
        )
    )
    return normalized_rows


def main() -> None:
    args = _parse_args()
    app = create_app()

    with app.app_context():
        if args.replace_existing:
            _remove_existing_chunk_seed_files()

        user_seed_keys = _load_user_seed_key_by_identity()
        post_signatures = _build_forum_post_seed_signature_index(user_seed_keys)
        forum_post_seed_keys_in_load_order = _load_forum_post_seed_keys_in_load_order()

        posts = list(db.session.scalars(select(ForumPost).order_by(ForumPost.id.asc())))
        post_seed_keys: dict[int, str] = {}
        if posts:
            post_seed_keys = {
                post.id: _resolve_post_seed_key(
                    post=post,
                    user_seed_keys=user_seed_keys,
                    post_signatures=post_signatures,
                )
                for post in posts
            }

        chunks = list(
            db.session.scalars(
                select(ForumPostChunk).order_by(
                    ForumPostChunk.post_id.asc(),
                    ForumPostChunk.chunk_version.asc(),
                    ForumPostChunk.chunk_index.asc(),
                    ForumPostChunk.id.asc(),
                )
            )
        )
        chunk_rows: list[dict[str, Any]]
        if chunks:
            chunk_rows = [
                {
                    "post_id": chunk.post_id,
                    "chunk_text": chunk.chunk_text,
                    "chunk_index": chunk.chunk_index,
                    "section_title": chunk.section_title,
                    "chunk_version": chunk.chunk_version,
                    "embedding_id": chunk.embedding_id,
                    "numeric_id": chunk.id,
                }
                for chunk in chunks
            ]
        else:
            chunk_rows = _load_manifest_chunk_rows()
            if chunk_rows and not post_seed_keys:
                post_seed_keys = dict(enumerate(forum_post_seed_keys_in_load_order, start=1))

        exported_chunks = 0
        for chunk in chunk_rows:
            post_seed_key = post_seed_keys.get(int(chunk["post_id"]))
            if not post_seed_key:
                raise ValueError(
                    f"Could not find a forum post seed key for chunk post_id={chunk['post_id']} "
                    f"chunk_version={chunk['chunk_version']} chunk_index={chunk['chunk_index']}."
                )

            chunk_seed_key = f"{post_seed_key}-chunk-v{int(chunk['chunk_version']):02d}-i{int(chunk['chunk_index']):02d}"
            payload = {
                "_seed_key": chunk_seed_key,
                "post_ref": f"forum_posts.{post_seed_key}",
                "chunk_text": chunk["chunk_text"],
                "chunk_index": chunk["chunk_index"],
                "section_title": chunk["section_title"],
                "chunk_version": chunk["chunk_version"],
                "embedding_id": chunk["embedding_id"],
            }
            _write_json(FORUM_POST_CHUNK_SEEDS_ROOT / f"{chunk_seed_key}.json", payload)
            exported_chunks += 1

        exported_faiss_assets = _export_faiss_assets()

        print("Forum RAG seed export complete.")
        print(f"- forum posts matched: {len(post_seed_keys)}")
        print(f"- forum_post_chunks exported: {exported_chunks}")
        print(f"- faiss assets exported: {exported_faiss_assets}")


if __name__ == "__main__":
    main()
