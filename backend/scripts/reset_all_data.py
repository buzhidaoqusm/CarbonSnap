"""
Clear all application table data and wipe `data/uploads`.

Usage (from repo root, with backend venv available):
  python backend/scripts/reset_all_data.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND_ROOT.parent
sys.path.insert(0, str(_BACKEND_ROOT))

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import Base
from app.db.maintenance import truncate_tables
from app.db.session import get_engine, get_sessionmaker


def uploads_root() -> Path:
    # Read at call time: UPLOAD_ROOT (or a test override) decides where the
    # script reads, writes and deletes.
    return Path(get_settings().upload_root)


def faiss_root() -> Path:
    # Read at call time: FORUM_RAG_FAISS_DIR (or a test override) decides
    # where the script reads, writes and deletes.
    return Path(get_settings().forum_rag_faiss_dir)


def _clear_all_table_data(session: Session) -> int:
    table_names = [name for name in Base.metadata.tables if name != "alembic_version"]
    truncate_tables(session, table_names)
    return len(table_names)


def _clear_uploads_directory() -> int:
    removed_entries = 0
    uploads_root().mkdir(parents=True, exist_ok=True)

    for child in uploads_root().iterdir():
        if child.name == ".gitkeep":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
        removed_entries += 1

    gitkeep_path = uploads_root() / ".gitkeep"
    if not gitkeep_path.exists():
        gitkeep_path.write_text("", encoding="utf-8")

    return removed_entries


def _clear_faiss_directory() -> int:
    removed_entries = 0
    faiss_root().mkdir(parents=True, exist_ok=True)

    for child in faiss_root().iterdir():
        if child.name == ".gitkeep":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
        removed_entries += 1

    gitkeep_path = faiss_root() / ".gitkeep"
    if not gitkeep_path.exists():
        gitkeep_path.write_text("", encoding="utf-8")

    return removed_entries


def main() -> None:
    with get_sessionmaker()() as session:
        Base.metadata.create_all(get_engine())
        cleared_table_count = _clear_all_table_data(session)
        removed_upload_entries = _clear_uploads_directory()
        removed_faiss_entries = _clear_faiss_directory()

        print("Database and uploads reset complete.")
        print(f"- cleared tables: {cleared_table_count}")
        print(f"- removed upload entries: {removed_upload_entries}")
        print(f"- removed faiss entries: {removed_faiss_entries}")


if __name__ == "__main__":
    main()
