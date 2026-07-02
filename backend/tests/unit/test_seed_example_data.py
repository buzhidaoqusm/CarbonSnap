from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from scripts import seed_example_data


def _make_temp_dir(name: str) -> Path:
    root = Path(__file__).resolve().parents[2] / ".tmp-test-artifacts"
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{name}-{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_restore_seed_faiss_assets_copies_seeded_manifest(monkeypatch):
    temp_root = _make_temp_dir("seed-faiss")
    seed_faiss_root = temp_root / "seeds-faiss"
    seed_faiss_root.mkdir(parents=True)
    (seed_faiss_root / "forum_rag.json").write_text('{"schema_version":1}', encoding="utf-8")

    faiss_root = temp_root / "runtime-faiss"
    faiss_root.mkdir(parents=True)
    (faiss_root / ".gitkeep").write_text("", encoding="utf-8")
    (faiss_root / "stale.json").write_text("stale", encoding="utf-8")

    monkeypatch.setattr(seed_example_data, "SEED_FAISS_ASSETS_ROOT", seed_faiss_root)
    monkeypatch.setattr(seed_example_data, "FAISS_ROOT", faiss_root)

    restored_count = seed_example_data._restore_seed_faiss_assets()

    assert restored_count == 1
    assert (faiss_root / "forum_rag.json").read_text(encoding="utf-8") == '{"schema_version":1}'
    assert not (faiss_root / "stale.json").exists()


def test_validate_seeded_forum_rag_assets_requires_manifest(monkeypatch):
    faiss_root = _make_temp_dir("missing-manifest")
    monkeypatch.setattr(seed_example_data, "FAISS_ROOT", faiss_root)

    with pytest.raises(FileNotFoundError):
        seed_example_data._validate_seeded_forum_rag_assets(forum_post_chunk_count=1)


def test_validate_seeded_forum_rag_assets_allows_empty_chunk_seed_without_manifest(monkeypatch):
    faiss_root = _make_temp_dir("empty-chunks")
    monkeypatch.setattr(seed_example_data, "FAISS_ROOT", faiss_root)

    seed_example_data._validate_seeded_forum_rag_assets(forum_post_chunk_count=0)


def test_seed_example_data_loads_content_topic_assignments_directly():
    assert "content_topic_assignments" in seed_example_data.TABLE_LOAD_ORDER
    assert "content_topic_assignments" in seed_example_data.TABLE_MODEL_MAP


def test_seed_example_data_loads_user_memory_items_directly():
    assert "user_memory_items" in seed_example_data.TABLE_LOAD_ORDER
    assert "user_memory_items" in seed_example_data.TABLE_MODEL_MAP
