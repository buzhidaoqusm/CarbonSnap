from __future__ import annotations

import re
from typing import Any

from flask import current_app


_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?。！？])\s+")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_forum_text(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", str(value or "").strip())


def chunk_forum_post(*, title: str, content: str, version: int) -> list[dict[str, Any]]:
    normalized_title = normalize_forum_text(title)
    normalized_content = str(content or "").strip()
    if not normalized_content:
        return [
            {
                "chunk_index": 0,
                "section_title": "Main",
                "chunk_version": version,
                "chunk_text": normalized_title,
            }
        ]

    target_tokens = int(current_app.config.get("FORUM_RAG_CHUNK_TARGET_TOKENS", 420) or 420)
    overlap_tokens = int(current_app.config.get("FORUM_RAG_CHUNK_OVERLAP_TOKENS", 70) or 70)

    segments = _build_segments(normalized_content, target_tokens=target_tokens)
    chunks: list[dict[str, Any]] = []
    current_tokens: list[str] = []

    for segment in segments:
        segment_tokens = segment.split()
        if current_tokens and len(current_tokens) + len(segment_tokens) > target_tokens:
            chunks.append(
                _build_chunk_payload(
                    title=normalized_title,
                    chunk_tokens=current_tokens,
                    chunk_index=len(chunks),
                    version=version,
                )
            )
            overlap = current_tokens[-overlap_tokens:] if overlap_tokens > 0 else []
            current_tokens = overlap[:]

        current_tokens.extend(segment_tokens)

    if current_tokens:
        chunks.append(
            _build_chunk_payload(
                title=normalized_title,
                chunk_tokens=current_tokens,
                chunk_index=len(chunks),
                version=version,
            )
        )

    return chunks or [
        {
            "chunk_index": 0,
            "section_title": "Main",
            "chunk_version": version,
            "chunk_text": normalized_title,
        }
    ]


def _build_segments(content: str, *, target_tokens: int) -> list[str]:
    paragraphs = [normalize_forum_text(item) for item in _PARAGRAPH_SPLIT_RE.split(content) if item.strip()]
    segments: list[str] = []

    for paragraph in paragraphs:
        tokens = paragraph.split()
        if len(tokens) <= target_tokens:
            segments.append(paragraph)
            continue

        sentences = [normalize_forum_text(item) for item in _SENTENCE_SPLIT_RE.split(paragraph) if item.strip()]
        if not sentences:
            sentences = [paragraph]

        current_tokens: list[str] = []
        for sentence in sentences:
            sentence_tokens = sentence.split()
            if current_tokens and len(current_tokens) + len(sentence_tokens) > target_tokens:
                segments.append(" ".join(current_tokens))
                current_tokens = []

            if len(sentence_tokens) > target_tokens:
                segments.extend(_split_token_block(sentence_tokens, target_tokens))
                current_tokens = []
                continue

            current_tokens.extend(sentence_tokens)

        if current_tokens:
            segments.append(" ".join(current_tokens))

    return segments


def _split_token_block(tokens: list[str], target_tokens: int) -> list[str]:
    return [
        " ".join(tokens[start : start + target_tokens])
        for start in range(0, len(tokens), target_tokens)
    ]


def _build_chunk_payload(
    *,
    title: str,
    chunk_tokens: list[str],
    chunk_index: int,
    version: int,
) -> dict[str, Any]:
    body = " ".join(chunk_tokens).strip()
    chunk_text = f"{title}\n\n{body}".strip() if title else body
    return {
        "chunk_index": chunk_index,
        "section_title": "Main",
        "chunk_version": version,
        "chunk_text": chunk_text,
    }
