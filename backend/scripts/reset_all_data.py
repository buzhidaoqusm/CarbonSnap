"""
Clear all application table data and wipe `data/uploads`.

Usage (from repo root, with backend venv available):
  python backend/scripts/reset_all_data.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from sqlalchemy import text

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _BACKEND_ROOT.parent
sys.path.insert(0, str(_BACKEND_ROOT))

from app import create_app
from app.extensions.db import db

UPLOADS_ROOT = _REPO_ROOT / "data" / "uploads"
FAISS_ROOT = _REPO_ROOT / "data" / "faiss"


def _is_sqlite() -> bool:
    return db.engine.dialect.name == "sqlite"


def _clear_all_table_data() -> int:
    table_names = sorted(
        table_name for table_name in db.metadata.tables.keys() if table_name != "alembic_version"
    )

    if _is_sqlite():
        db.session.execute(text("PRAGMA foreign_keys=OFF"))
        db.session.commit()

    try:
        for table_name in table_names:
            db.session.execute(text(f'DELETE FROM "{table_name}"'))
        if _is_sqlite():
            try:
                db.session.execute(text("DELETE FROM sqlite_sequence"))
            except Exception:
                pass
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    finally:
        if _is_sqlite():
            db.session.execute(text("PRAGMA foreign_keys=ON"))
            db.session.commit()

    return len(table_names)


def _clear_uploads_directory() -> int:
    removed_entries = 0
    UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)

    for child in UPLOADS_ROOT.iterdir():
        if child.name == ".gitkeep":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
        removed_entries += 1

    gitkeep_path = UPLOADS_ROOT / ".gitkeep"
    if not gitkeep_path.exists():
        gitkeep_path.write_text("", encoding="utf-8")

    return removed_entries


def _clear_faiss_directory() -> int:
    removed_entries = 0
    FAISS_ROOT.mkdir(parents=True, exist_ok=True)

    for child in FAISS_ROOT.iterdir():
        if child.name == ".gitkeep":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
        removed_entries += 1

    gitkeep_path = FAISS_ROOT / ".gitkeep"
    if not gitkeep_path.exists():
        gitkeep_path.write_text("", encoding="utf-8")

    return removed_entries


def main() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        cleared_table_count = _clear_all_table_data()
        removed_upload_entries = _clear_uploads_directory()
        removed_faiss_entries = _clear_faiss_directory()

        print("Database and uploads reset complete.")
        print(f"- cleared tables: {cleared_table_count}")
        print(f"- removed upload entries: {removed_upload_entries}")
        print(f"- removed faiss entries: {removed_faiss_entries}")


if __name__ == "__main__":
    main()
