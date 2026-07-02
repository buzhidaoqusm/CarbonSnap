from app.extensions.db import db
from app.models.forum import ForumPost
from app.models.user import User
from app.repositories.forum import forum_repository


def _make_user():
    user = User(username="chunk-user", email="chunk-user@example.com", password_hash="pw")
    db.session.add(user)
    db.session.flush()
    return user


class TestForumRepositoryChunkPersistence:
    def test_save_post_chunks_persists_structured_metadata(self):
        user = _make_user()
        post = ForumPost(author_id=user.id, title="T", content="C")
        db.session.add(post)
        db.session.commit()

        forum_repository.save_post_chunks(
            post.id,
            [
                {
                    "chunk_text": "Chunk body",
                    "chunk_index": 0,
                    "section_title": "Main",
                    "chunk_version": 2,
                    "embedding_id": "chunk-0",
                }
            ],
        )

        chunks = forum_repository.get_chunks_by_post(post.id)
        assert len(chunks) == 1
        assert chunks[0].chunk_index == 0
        assert chunks[0].section_title == "Main"
        assert chunks[0].chunk_version == 2
        assert chunks[0].embedding_id == "chunk-0"

    def test_get_latest_chunk_version_returns_max_version(self):
        user = _make_user()
        post = ForumPost(author_id=user.id, title="T", content="C")
        db.session.add(post)
        db.session.commit()

        forum_repository.save_post_chunks(
            post.id,
            [
                {
                    "chunk_text": "Chunk body",
                    "chunk_index": 0,
                    "section_title": "Main",
                    "chunk_version": 4,
                }
            ],
        )

        assert forum_repository.get_latest_chunk_version(post.id) == 4
