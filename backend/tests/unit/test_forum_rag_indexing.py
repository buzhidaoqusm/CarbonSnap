from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from contextlib import contextmanager

import pytest

from app.ai.rag.indexing.forum_index import ForumRagChunkRecord, ForumRagIndex
from app.ai.rag.indexing import forum_index as forum_index_module


def _fake_embedder(mapping: dict[str, list[float]]):
    def _embed(texts: list[str]) -> list[list[float]]:
        return [mapping[text] for text in texts]

    return _embed


@contextmanager
def _forum_rag_temp_dir():
    root = Path.cwd().parent / "data" / "forum-rag-test"
    root.mkdir(parents=True, exist_ok=True)
    temp_dir = root / uuid.uuid4().hex
    temp_dir.mkdir()
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_forum_rag_index_upsert_search_delete_round_trip(monkeypatch):
    monkeypatch.setattr(forum_index_module, "_FAISS_AVAILABLE", False)

    with _forum_rag_temp_dir() as storage_dir:
        index = ForumRagIndex(
            storage_dir=storage_dir,
            index_name="forum_rag_test",
            embedder=_fake_embedder(
                {
                    "Bottle recycling tips": [1.0, 0.0],
                    "Glass jar guidance": [0.0, 1.0],
                    "Find bottle advice": [1.0, 0.0],
                }
            ),
        )

        index.upsert(
            [
                ForumRagChunkRecord(
                    chunk_id="chunk-a",
                    post_id=11,
                    chunk_index=0,
                    section_title="Main",
                    chunk_version=1,
                    chunk_text="Bottle recycling tips",
                ),
                ForumRagChunkRecord(
                    chunk_id="chunk-b",
                    post_id=12,
                    chunk_index=0,
                    section_title="Main",
                    chunk_version=1,
                    chunk_text="Glass jar guidance",
                ),
            ]
        )

        manifest_path = storage_dir / "forum_rag_test.json"
        assert manifest_path.exists()

        hits = index.search("Find bottle advice", top_k=2)
        assert [hit.chunk_id for hit in hits] == ["chunk-a", "chunk-b"]
        assert hits[0].score == pytest.approx(1.0)

        reloaded = ForumRagIndex(
            storage_dir=storage_dir,
            index_name="forum_rag_test",
            embedder=_fake_embedder(
                {
                    "Find bottle advice": [1.0, 0.0],
                }
            ),
        )

        reloaded_hits = reloaded.search("Find bottle advice", top_k=2)
        assert [hit.chunk_id for hit in reloaded_hits] == ["chunk-a", "chunk-b"]

        removed = reloaded.delete(["chunk-a"])
        assert removed == 1
        assert [hit.chunk_id for hit in reloaded.search("Find bottle advice", top_k=2)] == [
            "chunk-b"
        ]


def test_forum_rag_index_upsert_replaces_existing_chunk_id(monkeypatch):
    monkeypatch.setattr(forum_index_module, "_FAISS_AVAILABLE", False)

    with _forum_rag_temp_dir() as storage_dir:
        index = ForumRagIndex(
            storage_dir=storage_dir,
            index_name="forum_rag_replace",
            embedder=_fake_embedder(
                {
                    "Bottle advice v1": [1.0, 0.0],
                    "Bottle advice v2": [0.0, 1.0],
                    "Bottle advice search": [0.0, 1.0],
                }
            ),
        )

        index.upsert(
            [
                ForumRagChunkRecord(
                    chunk_id="chunk-a",
                    post_id=21,
                    chunk_index=0,
                    section_title="Main",
                    chunk_version=1,
                    chunk_text="Bottle advice v1",
                )
            ]
        )
        index.upsert(
            [
                ForumRagChunkRecord(
                    chunk_id="chunk-a",
                    post_id=21,
                    chunk_index=1,
                    section_title="Details",
                    chunk_version=2,
                    chunk_text="Bottle advice v2",
                )
            ]
        )

        hits = index.search("Bottle advice search", top_k=1)
        assert len(hits) == 1
        assert hits[0].chunk_id == "chunk-a"
        assert hits[0].chunk_version == 2
        assert hits[0].chunk_index == 1
        assert hits[0].section_title == "Details"
