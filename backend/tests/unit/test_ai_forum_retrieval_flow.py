from __future__ import annotations

import json
import uuid

from werkzeug.security import generate_password_hash

from app.extensions.db import db
from app.models.forum import ForumPost
from app.models.user import User
from app.services.ai import ai_conversation_service
from app.services.forum import forum_indexing_service


def _make_user(username: str = "forumflow", email: str = "forumflow@example.com") -> User:
    unique_suffix = uuid.uuid4().hex[:8]
    user = User(
        username=f"{username}_{unique_suffix}",
        email=f"{unique_suffix}_{email}",
        password_hash=generate_password_hash("password123"),
    )
    db.session.add(user)
    db.session.flush()
    return user


def test_complete_chat_message_uses_real_forum_retrieval_for_chinese_plastic_bottle_query(
    monkeypatch,
):
    user = _make_user()
    diy_post = ForumPost(
        author_id=user.id,
        title="Plastic Bottle Lantern DIY",
        content="Reuse a clean plastic bottle to make a lantern craft with ribbon and a small LED light.",
    )
    battery_post = ForumPost(
        author_id=user.id,
        title="Battery Sorting Guide",
        content="Separate used batteries before taking them to a drop-off point.",
    )
    db.session.add_all([diy_post, battery_post])
    db.session.commit()

    forum_indexing_service.reindex_post(
        post_id=diy_post.id,
        title=diy_post.title,
        content=diy_post.content,
    )
    forum_indexing_service.reindex_post(
        post_id=battery_post.id,
        title=battery_post.title,
        content=battery_post.content,
    )

    def fake_chat_with_openrouter(**kwargs):
        system_prompt = kwargs["system_prompt"]
        assert "Plastic Bottle Lantern DIY" in system_prompt
        assert f"/forum/posts/{diy_post.id}" in system_prompt
        return {
            "reply": f"You can try [Plastic Bottle Lantern DIY](/forum/posts/{diy_post.id}).",
            "model": "test-model",
            "usage": {},
        }

    monkeypatch.setattr(ai_conversation_service, "chat_with_openrouter", fake_chat_with_openrouter)

    result = ai_conversation_service.complete_chat_message(
        user_id=user.id,
        message="有没有比较好的回收塑料瓶的方法",
        history=[],
        title="Plastic bottle forum flow",
        decision={
            "intent": "general_chat",
            "should_retrieve_forum": True,
            "target_case_id": None,
            "context": {},
        },
    )

    assistant_message = db.session.get(
        ai_conversation_service.AIMessage, result["assistant_message_id"]
    )
    assistant_payload = json.loads(assistant_message.content_json)

    assert result["forum_references"] == [
        {
            "reference_id": f"forum-post-{diy_post.id}",
            "post_id": diy_post.id,
            "title": "Plastic Bottle Lantern DIY",
            "url": f"/forum/posts/{diy_post.id}",
        }
    ]
    assert assistant_payload["forum_references"] == result["forum_references"]
