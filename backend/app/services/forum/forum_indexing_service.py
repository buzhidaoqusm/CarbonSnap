from __future__ import annotations

from typing import Any

from flask import current_app

from app.ai.rag.chunking import chunk_forum_post
from app.ai.rag.indexing import ForumRagChunkRecord, build_forum_rag_index
from app.repositories.forum import forum_repository
from app.services.ai.forum_graph_sync_service import remove_forum_post_graph, sync_forum_post_graph

_DEFAULT_BUILD_FORUM_RAG_INDEX = build_forum_rag_index


def reindex_post(*, post_id: int, title: str, content: str) -> list[dict[str, Any]]:
    current_chunks = forum_repository.get_chunks_by_post(post_id)
    previous_embedding_ids = [
        str(chunk.embedding_id).strip()
        for chunk in current_chunks
        if getattr(chunk, "embedding_id", None)
    ]
    next_version = max(forum_repository.get_latest_chunk_version(post_id), 0) + 1
    chunk_payloads = chunk_forum_post(title=title, content=content, version=next_version)

    for item in chunk_payloads:
        item["post_id"] = post_id
        item["embedding_id"] = _build_embedding_id(
            post_id=post_id,
            chunk_version=next_version,
            chunk_index=item["chunk_index"],
        )

    _upsert_chunks(chunk_payloads)
    saved_rows = forum_repository.save_post_chunks(
        post_id,
        chunk_payloads,
    )
    _remove_vectors(previous_embedding_ids)
    post = forum_repository.get_post_by_id(post_id)
    remove_forum_post_graph(post_id=post_id)
    sync_forum_post_graph(
        post_id=post_id,
        title=title,
        content=content,
        author_id=getattr(post, "author_id", None),
        created_at=getattr(post, "created_at", None),
        chunks=saved_rows,
    )

    return [
        {
            "id": row.id,
            "post_id": row.post_id,
            "chunk_index": row.chunk_index,
            "chunk_version": row.chunk_version,
            "embedding_id": row.embedding_id,
        }
        for row in saved_rows
    ]


def remove_post_index(post_id: int) -> None:
    current_chunks = forum_repository.get_chunks_by_post(post_id)
    embedding_ids = [
        str(chunk.embedding_id).strip()
        for chunk in current_chunks
        if getattr(chunk, "embedding_id", None)
    ]
    forum_repository.save_post_chunks(post_id, [])
    _remove_vectors(embedding_ids)
    remove_forum_post_graph(post_id=post_id)


def rebuild_all_post_indexes() -> int:
    indexed_count = 0
    for post in forum_repository.list_all_published_posts():
        reindex_post(post_id=post.id, title=post.title, content=post.content)
        indexed_count += 1
    return indexed_count


def _build_embedding_id(*, post_id: int, chunk_version: int, chunk_index: int) -> str:
    return f"post-{post_id}-v{chunk_version}-c{chunk_index}"


def _upsert_chunks(chunk_payloads: list[dict[str, Any]]) -> None:
    if not chunk_payloads:
        return
    if _should_skip_live_indexing():
        return

    index = build_forum_rag_index()
    try:
        index.upsert(
            [
                ForumRagChunkRecord(
                    chunk_id=str(item["embedding_id"]),
                    post_id=int(item.get("post_id") or 0),
                    chunk_index=int(item["chunk_index"]),
                    section_title=item.get("section_title"),
                    chunk_version=int(item["chunk_version"]),
                    chunk_text=str(item["chunk_text"]),
                )
                for item in chunk_payloads
            ]
        )
    except Exception:
        # Forum CRUD should stay available even if vector indexing is temporarily unavailable.
        return


def _remove_vectors(embedding_ids: list[str]) -> None:
    if not embedding_ids:
        return

    index = build_forum_rag_index()
    index.delete(embedding_ids)


def _should_skip_live_indexing() -> bool:
    if not current_app.config.get("TESTING"):
        return False

    if current_app.config.get("FORUM_RAG_ENABLE_TEST_INDEXING"):
        return False

    return build_forum_rag_index is _DEFAULT_BUILD_FORUM_RAG_INDEX
