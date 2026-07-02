import uuid

from werkzeug.security import generate_password_hash

from app.extensions.db import db
from app.models.memory import UserMemoryItem
from app.models.user import User
from app.repositories.ai import memory_repository


def _make_user(username: str = "memory", email: str = "memory@example.com") -> User:
    unique_suffix = uuid.uuid4().hex[:8]
    user = User(
        username=f"{username}_{unique_suffix}",
        email=f"{unique_suffix}_{email}",
        password_hash=generate_password_hash("password123"),
    )
    db.session.add(user)
    db.session.flush()
    return user


class TestUserMemoryItemModel:
    def test_defaults_are_initialized(self):
        user = _make_user()

        item = UserMemoryItem(
            user_id=user.id,
            memory_type="response_style",
            memory_key="response_style",
            value_json='{"value":"concise"}',
            source_type="explicit_chat",
        )
        db.session.add(item)
        db.session.flush()

        assert item.status == "active"
        assert item.conversation_id is None
        assert item.source_message_id is None
        assert item.created_at is not None
        assert item.updated_at is not None


class TestMemoryRepository:
    def test_replace_active_memory_item_soft_deletes_old_value(self):
        user = _make_user("replace", "replace@example.com")

        first = memory_repository.create_memory_item(
            user_id=user.id,
            memory_type="response_style",
            memory_key="response_style",
            value_json='{"value":"concise"}',
            source_type="explicit_chat",
        )
        second = memory_repository.replace_memory_item(
            user_id=user.id,
            memory_type="response_style",
            memory_key="response_style",
            value_json='{"value":"detailed"}',
            source_type="manual_edit",
        )

        db.session.refresh(first)
        assert first.status == "deleted"
        assert second.status == "active"

    def test_list_active_memory_items_ignores_deleted_rows(self):
        user = _make_user("active", "active@example.com")
        item = memory_repository.create_memory_item(
            user_id=user.id,
            memory_type="topic_interest",
            memory_key="battery",
            value_json='{"topic":"battery"}',
            source_type="explicit_chat",
        )

        memory_repository.soft_delete_memory_item(item.id, user.id)
        active_items = memory_repository.list_active_memory_items(user.id)

        assert active_items == []
