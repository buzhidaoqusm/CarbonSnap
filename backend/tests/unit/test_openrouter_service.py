from __future__ import annotations

from app.services.ai import openrouter_service


def test_build_messages_uses_default_text_for_image_only_message():
    image_data_url = "data:image/png;base64,abc123"

    messages = openrouter_service.build_messages(
        user_message="",
        image_data_url=image_data_url,
    )

    user_content = messages[-1]["content"]

    assert user_content == [
        {"type": "text", "text": "Please analyze this image."},
        {"type": "image_url", "image_url": {"url": image_data_url}},
    ]
