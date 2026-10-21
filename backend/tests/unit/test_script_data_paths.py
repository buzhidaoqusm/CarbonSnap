"""The reset and seed scripts work on the directories the settings name.

They used to clear data/uploads and data/faiss under the repository whatever
UPLOAD_ROOT and FORUM_RAG_FAISS_DIR said, which once emptied a developer's
real uploads during a run meant for a scratch directory.

Each test checks where a script is about to write before letting it delete
anything, so a regression fails the assertion instead of touching real data.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import reset_all_data, seed_example_data


def _target(module, name: str) -> Path:
    # The directory the script would use now: the function if it has one,
    # else the old module constant.
    function = getattr(module, name.lower(), None)
    return Path(function() if callable(function) else getattr(module, name))


@pytest.fixture
def scratch(tmp_path, override_settings):
    uploads, faiss = tmp_path / "uploads", tmp_path / "faiss"
    for directory in (uploads, faiss):
        directory.mkdir()
        (directory / "user-file.bin").write_bytes(b"x")
        (directory / ".gitkeep").write_text("")
    override_settings(upload_root=uploads, forum_rag_faiss_dir=faiss)
    return uploads, faiss


def test_reset_clears_the_configured_directories(scratch):
    uploads, faiss = scratch
    assert _target(reset_all_data, "UPLOADS_ROOT") == uploads
    assert _target(reset_all_data, "FAISS_ROOT") == faiss

    assert reset_all_data._clear_uploads_directory() == 1
    assert reset_all_data._clear_faiss_directory() == 1

    assert [p.name for p in uploads.iterdir()] == [".gitkeep"]
    assert [p.name for p in faiss.iterdir()] == [".gitkeep"]


def test_seeding_restores_into_the_configured_directories(scratch):
    uploads, faiss = scratch
    assert _target(seed_example_data, "UPLOADS_ROOT") == uploads
    assert _target(seed_example_data, "FAISS_ROOT") == faiss

    restored_uploads = seed_example_data._restore_seed_upload_assets()
    restored_faiss = seed_example_data._restore_seed_faiss_assets()

    assert restored_uploads > 0 and restored_faiss > 0
    assert any(p.is_dir() for p in uploads.iterdir())
    assert (faiss / "forum_rag.json").exists()
