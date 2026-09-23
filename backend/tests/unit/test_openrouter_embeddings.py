from __future__ import annotations

import pytest

from app.services.ai import openrouter_service


class _EmbeddingItem:
    def __init__(self, index: int, embedding: list[float]) -> None:
        self.index = index
        self.embedding = embedding


class _FakeEmbeddingsClient:
    def __init__(self, response_items: list[_EmbeddingItem]) -> None:
        self._response_items = response_items
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return type("EmbeddingResponse", (), {"data": self._response_items})()


class _FakeClient:
    def __init__(self, response_items: list[_EmbeddingItem]) -> None:
        self.embeddings = _FakeEmbeddingsClient(response_items)


def test_embed_texts_normalizes_input_and_restores_response_order(monkeypatch):
    fake_client = _FakeClient(
        [
            _EmbeddingItem(index=1, embedding=[0.0, 1.0]),
            _EmbeddingItem(index=0, embedding=[1.0, 0.0]),
        ]
    )

    monkeypatch.setattr(openrouter_service, "_get_client", lambda: fake_client)
    monkeypatch.setattr(openrouter_service, "_build_extra_headers", lambda: {})

    vectors = openrouter_service.embed_texts(
        ["  first   chunk  ", "second\nchunk"],
        model="forum-rag-embed",
    )

    assert fake_client.embeddings.calls[0]["model"] == "forum-rag-embed"
    assert fake_client.embeddings.calls[0]["input"] == ["first chunk", "second chunk"]
    assert vectors == [[1.0, 0.0], [0.0, 1.0]]


def test_embed_texts_rejects_blank_input(monkeypatch):
    fake_client = _FakeClient([_EmbeddingItem(index=0, embedding=[1.0, 0.0])])

    monkeypatch.setattr(openrouter_service, "_get_client", lambda: fake_client)
    monkeypatch.setattr(openrouter_service, "_build_extra_headers", lambda: {})

    with pytest.raises(ValueError):
        openrouter_service.embed_texts(["   "], model="forum-rag-embed")

    assert fake_client.embeddings.calls == []
