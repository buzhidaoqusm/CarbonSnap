from __future__ import annotations

from app.extensions.db import db
from app.models.forum import ForumPost
from app.models.user import User
from app.repositories.forum import forum_repository
from app.services.forum import forum_indexing_service


def _make_user() -> User:
    user = User(username="index-user", email="index-user@example.com", password_hash="pw")
    db.session.add(user)
    db.session.flush()
    return user


class _FakeIndex:
    def __init__(self) -> None:
        self.upserts = []
        self.deletes = []

    def upsert(self, chunks):
        self.upserts.append(list(chunks))
        return list(chunks)

    def delete(self, chunk_ids):
        self.deletes.append(list(chunk_ids))
        return len(chunk_ids)


def test_reindex_post_persists_chunks_and_updates_rag_index(monkeypatch, app):
    with app.app_context():
        user = _make_user()
        post = ForumPost(author_id=user.id, title="Bottle", content="Recycle this bottle carefully.")
        db.session.add(post)
        db.session.commit()

        fake_index = _FakeIndex()
        graph_calls = {"removed": [], "synced": []}
        monkeypatch.setattr(forum_indexing_service, "build_forum_rag_index", lambda: fake_index)
        monkeypatch.setattr(
            forum_indexing_service,
            "remove_forum_post_graph",
            lambda **kwargs: graph_calls["removed"].append(kwargs) or {"removed": True},
        )
        monkeypatch.setattr(
            forum_indexing_service,
            "sync_forum_post_graph",
            lambda **kwargs: graph_calls["synced"].append(kwargs) or {"synced": True},
        )

        rows = forum_indexing_service.reindex_post(
            post_id=post.id,
            title=post.title,
            content=post.content,
        )

        saved_chunks = forum_repository.get_chunks_by_post(post.id)

        assert rows
        assert fake_index.upserts
        assert saved_chunks[0].embedding_id == f"post-{post.id}-v1-c0"
        assert graph_calls["removed"] == [{"post_id": post.id}]
        assert graph_calls["synced"][0]["post_id"] == post.id
        assert graph_calls["synced"][0]["chunks"] == saved_chunks


def test_remove_post_index_deletes_chunk_rows_and_vector_entries(monkeypatch, app):
    with app.app_context():
        user = _make_user()
        post = ForumPost(author_id=user.id, title="Bottle", content="Recycle this bottle carefully.")
        db.session.add(post)
        db.session.commit()
        forum_repository.save_post_chunks(
            post.id,
            [
                {
                    "chunk_text": "Bottle advice",
                    "chunk_index": 0,
                    "section_title": "Main",
                    "chunk_version": 1,
                    "embedding_id": f"post-{post.id}-v1-c0",
                }
            ],
        )

        fake_index = _FakeIndex()
        graph_calls = []
        monkeypatch.setattr(forum_indexing_service, "build_forum_rag_index", lambda: fake_index)
        monkeypatch.setattr(
            forum_indexing_service,
            "remove_forum_post_graph",
            lambda **kwargs: graph_calls.append(kwargs) or {"removed": True},
        )

        forum_indexing_service.remove_post_index(post.id)

        assert forum_repository.get_chunks_by_post(post.id) == []
        assert fake_index.deletes == [[f"post-{post.id}-v1-c0"]]
        assert graph_calls == [{"post_id": post.id}]
