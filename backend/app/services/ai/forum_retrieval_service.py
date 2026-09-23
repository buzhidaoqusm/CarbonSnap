from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from flask import current_app

from app.ai.rag.indexing import build_forum_rag_index
from app.repositories.forum import forum_repository
from app.services.ai.guardrails import scan_retrieved_text_for_injection

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]+")
_WHITESPACE_RE = re.compile(r"\s+")
_QUERY_EXPANSION_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("塑料瓶", "塑料瓶子"), ("plastic bottle", "plastic", "bottle")),
    (("回收", "可回收"), ("recycle", "recycling")),
    (("再利用", "二次利用", "手工", "创意"), ("reuse", "upcycle", "upcycling", "diy", "craft")),
    (("方法", "做法", "建议", "点子"), ("ideas",)),
    (("灯笼",), ("lantern",)),
    (("电池", "干电池"), ("battery", "batteries")),
    (("玻璃罐", "玻璃瓶", "罐子"), ("glass jar", "glass bottle", "jar")),
)


def retrieve_forum_references(
    *,
    query: str,
    limit: int | None = None,
) -> dict[str, Any]:
    normalized_query = _normalize_text(query)
    if not normalized_query:
        return {"query": "", "candidates": []}

    effective_query = _expand_retrieval_query(normalized_query)
    keyword_hits = _keyword_recall(effective_query)
    vector_hits = _vector_recall(effective_query)
    fused_hits = _fuse_hits(keyword_hits=keyword_hits, vector_hits=vector_hits)
    aggregated = _aggregate_hits_by_post(fused_hits)
    safe_candidates = [item for item in aggregated if item.get("guardrail_status") == "passed"]
    blocked_candidates = [item for item in aggregated if item.get("guardrail_status") == "blocked"]

    configured_final_top_k = int(current_app.config.get("FORUM_RAG_FINAL_TOP_K", 4) or 4)
    max_candidates = max(int(limit or 0), 1) if limit is not None else configured_final_top_k
    return {
        "query": normalized_query,
        "candidates": safe_candidates[:max_candidates],
        "blocked_candidates": blocked_candidates,
    }


def build_forum_prompt_block(candidates: list[dict[str, Any]]) -> str:
    if not candidates:
        return ""

    lines = ["Forum post references available for this turn:"]
    for item in candidates:
        lines.append(f"- reference_id: {item['reference_id']}")
        lines.append(f"  title: {item['title']}")
        lines.append(f"  url: {item['url']}")
        lines.append(f"  excerpt: {item['excerpt']}")
        lines.append(f"  retrieval_reason: {item['retrieval_reason']}")

    lines.extend(
        [
            "Citation rules:",
            "- Use forum posts only when they truly help answer the user.",
            "- If you use forum-derived advice, quote the source inline with the exact markdown link [Title](URL).",
            "- Never invent forum titles, post ids, or URLs.",
            "- If you use one or more forum posts, end with a short 'Sources' section that only lists the links you actually used.",
        ]
    )
    return "\n".join(lines)


def extract_used_forum_references(
    text: str,
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized_text = str(text or "")
    if not normalized_text or not candidates:
        return []

    matched: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    lowered_text = normalized_text.lower()

    for item in candidates:
        url = str(item.get("url", "")).strip()
        title = str(item.get("title", "")).strip()
        if not url or url in seen_urls:
            continue
        if url in normalized_text or title.lower() in lowered_text:
            matched.append(_serialize_reference(item))
            seen_urls.add(url)
    return matched


def resolve_explicit_forum_references(
    raw_references: list[dict[str, Any]] | None,
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not raw_references or not candidates:
        return []

    by_url = {item["url"]: item for item in candidates if item.get("url")}
    by_post_id = {item["post_id"]: item for item in candidates if item.get("post_id") is not None}
    by_title = {
        str(item["title"]).strip().lower(): item for item in candidates if item.get("title")
    }
    resolved: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for item in raw_references:
        if not isinstance(item, dict):
            continue
        candidate = None
        url = str(item.get("url", "")).strip()
        title = str(item.get("title", "")).strip().lower()
        post_id = item.get("post_id")

        if url and url in by_url:
            candidate = by_url[url]
        elif post_id in by_post_id:
            candidate = by_post_id[post_id]
        elif title and title in by_title:
            candidate = by_title[title]

        if candidate is None or candidate["url"] in seen_urls:
            continue
        resolved.append(_serialize_reference(candidate))
        seen_urls.add(candidate["url"])

    return resolved


def _keyword_recall(query: str) -> list[dict[str, Any]]:
    scored_hits: list[dict[str, Any]] = []
    for chunk, post in forum_repository.list_active_chunks():
        score = _score_keyword_match(query=query, title=post.title, text=chunk.chunk_text)
        if score <= 0:
            continue
        scored_hits.append(
            {
                "post_id": post.id,
                "title": post.title,
                "url": _build_post_url(post.id),
                "chunk_text": chunk.chunk_text,
                "embedding_id": chunk.embedding_id,
                "chunk_index": chunk.chunk_index,
                "chunk_version": chunk.chunk_version,
                "score": score,
                "source": "keyword",
                "excerpt": _build_excerpt(chunk.chunk_text, query),
                "created_at": getattr(post, "created_at", None),
            }
        )

    scored_hits.sort(
        key=lambda item: (
            float(item["score"]),
            getattr(item.get("created_at"), "timestamp", lambda: 0.0)(),
            int(item["post_id"]),
        ),
        reverse=True,
    )
    top_k = int(current_app.config.get("FORUM_RAG_KEYWORD_TOP_K", 8) or 8)
    return scored_hits[:top_k]


def _vector_recall(query: str) -> list[dict[str, Any]]:
    try:
        top_k = int(current_app.config.get("FORUM_RAG_VECTOR_TOP_K", 8) or 8)
        matches = build_forum_rag_index().search(query, top_k=top_k)
    except Exception:
        return []
    if not matches:
        return []

    rows = forum_repository.list_active_chunks_by_embedding_ids(
        [str(item.chunk_id).strip() for item in matches if getattr(item, "chunk_id", None)]
    )
    row_by_embedding_id = {
        str(chunk.embedding_id): (chunk, post)
        for chunk, post in rows
        if getattr(chunk, "embedding_id", None)
    }

    scored_hits: list[dict[str, Any]] = []
    for match in matches:
        embedding_id = str(match.chunk_id).strip()
        row = row_by_embedding_id.get(embedding_id)
        if row is None:
            continue
        chunk, post = row
        scored_hits.append(
            {
                "post_id": post.id,
                "title": post.title,
                "url": _build_post_url(post.id),
                "chunk_text": chunk.chunk_text,
                "embedding_id": embedding_id,
                "chunk_index": chunk.chunk_index,
                "chunk_version": chunk.chunk_version,
                "score": float(match.score),
                "source": "vector",
                "excerpt": _build_excerpt(chunk.chunk_text, query),
                "created_at": getattr(post, "created_at", None),
            }
        )
    return scored_hits


def _fuse_hits(
    *,
    keyword_hits: list[dict[str, Any]],
    vector_hits: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: dict[tuple[int, str | None, int, int], dict[str, Any]] = {}

    for source_hits in (keyword_hits, vector_hits):
        for rank, item in enumerate(source_hits, start=1):
            key = (
                int(item["post_id"]),
                item.get("embedding_id"),
                int(item["chunk_version"]),
                int(item["chunk_index"]),
            )
            current = merged.setdefault(
                key,
                {
                    **item,
                    "fusion_score": 0.0,
                    "sources": set(),
                },
            )
            current["fusion_score"] += 1.0 / (rank + 60)
            current["sources"].add(item["source"])
            current.setdefault("source_scores", {})
            current["source_scores"][item["source"]] = max(
                float(current["source_scores"].get(item["source"], 0.0)),
                float(item["score"]),
            )
            current["score"] = max(float(current["score"]), float(item["score"]))

    fused_hits = list(merged.values())
    fused_hits.sort(
        key=lambda item: (
            float(item["fusion_score"]),
            float(item["score"]),
            getattr(item.get("created_at"), "timestamp", lambda: 0.0)(),
        ),
        reverse=True,
    )
    return fused_hits


def _aggregate_hits_by_post(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[int, dict[str, Any]] = {}
    excerpts_by_post: dict[int, list[str]] = defaultdict(list)

    for item in hits:
        post_id = int(item["post_id"])
        entry = grouped.setdefault(
            post_id,
            {
                "reference_id": f"forum-post-{post_id}",
                "post_id": post_id,
                "title": item["title"],
                "url": item["url"],
                "score": 0.0,
                "score_breakdown": {"keyword": 0.0, "vector": 0.0, "fusion": 0.0},
                "retrieval_reason": set(),
                "matched_chunk_count": 0,
                "guardrail_status": "passed",
                "guardrail_reason": "clean",
                "guardrail_matches": [],
            },
        )
        entry["score"] += float(item["fusion_score"])
        entry["score_breakdown"]["fusion"] += float(item["fusion_score"])
        for source, score in (item.get("source_scores") or {}).items():
            if source in {"keyword", "vector"}:
                entry["score_breakdown"][source] = max(
                    float(entry["score_breakdown"].get(source, 0.0)),
                    float(score),
                )
        entry["retrieval_reason"].update(item["sources"])
        entry["matched_chunk_count"] += 1
        guardrail_scan = scan_retrieved_text_for_injection(
            f"{item.get('title', '')}\n{item.get('chunk_text', '')}"
        )
        if guardrail_scan["injection_flagged"]:
            entry["guardrail_status"] = "blocked"
            entry["guardrail_reason"] = guardrail_scan["reason"]
            entry["guardrail_matches"] = guardrail_scan["matched"]

        excerpt = str(item.get("excerpt", "")).strip()
        if (
            excerpt
            and excerpt not in excerpts_by_post[post_id]
            and len(excerpts_by_post[post_id]) < 2
        ):
            excerpts_by_post[post_id].append(excerpt)

    aggregated: list[dict[str, Any]] = []
    for post_id, entry in grouped.items():
        aggregated.append(
            {
                **entry,
                "excerpt": " ".join(excerpts_by_post.get(post_id) or [])[:500].strip(),
                "retrieval_reason": "+".join(sorted(entry["retrieval_reason"])) or "keyword",
            }
        )

    aggregated.sort(
        key=lambda item: (
            float(item["score"]),
            int(item["matched_chunk_count"]),
            int(item["post_id"]),
        ),
        reverse=True,
    )
    return aggregated


def _score_keyword_match(*, query: str, title: str, text: str) -> float:
    normalized_query = _normalize_text(query)
    normalized_title = _normalize_text(title)
    normalized_text = _normalize_text(text)
    if not normalized_query or not normalized_text:
        return 0.0

    score = 0.0
    if normalized_query in normalized_title:
        score += 3.5
    if normalized_query in normalized_text:
        score += 2.5

    query_tokens = _tokenize(normalized_query)
    if not query_tokens:
        return score

    title_tokens = set(_tokenize(normalized_title))
    text_tokens = set(_tokenize(normalized_text))
    total_tokens = len(query_tokens)
    matched_tokens = 0

    for token in query_tokens:
        if token in title_tokens:
            matched_tokens += 1
            score += 1.5
        elif token in text_tokens:
            matched_tokens += 1
            score += 0.8

    coverage = matched_tokens / max(total_tokens, 1)
    return score + coverage


def _expand_retrieval_query(query: str) -> str:
    normalized_query = _normalize_text(query)
    if not normalized_query:
        return ""

    expanded_terms: list[str] = [normalized_query]
    lowered_query = normalized_query.lower()

    for matchers, aliases in _QUERY_EXPANSION_RULES:
        if any(str(matcher).lower() in lowered_query for matcher in matchers):
            for alias in aliases:
                normalized_alias = _normalize_text(alias)
                if normalized_alias and normalized_alias not in expanded_terms:
                    expanded_terms.append(normalized_alias)

    if "塑料瓶" in normalized_query and any(
        marker in normalized_query for marker in ("方法", "做法", "建议", "点子", "再利用", "创意")
    ):
        for alias in ("reuse", "upcycle", "diy", "craft", "lantern"):
            if alias not in expanded_terms:
                expanded_terms.append(alias)

    return " ".join(expanded_terms)


def _build_excerpt(text: str, query: str) -> str:
    normalized = _normalize_text(text)
    if not normalized:
        return ""

    lowered = normalized.lower()
    query_tokens = _tokenize(query)
    start = 0
    for token in query_tokens:
        index = lowered.find(token.lower())
        if index >= 0:
            start = max(index - 80, 0)
            break

    excerpt = normalized[start : start + 220].strip()
    if start > 0:
        excerpt = f"...{excerpt}"
    if start + 220 < len(normalized):
        excerpt = f"{excerpt}..."
    return excerpt


def _normalize_text(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", str(value or "").strip())


def _tokenize(value: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(str(value or "").lower()) if token.strip()]


def _build_post_url(post_id: int) -> str:
    return f"/forum/posts/{post_id}"


def _serialize_reference(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "reference_id": item.get("reference_id") or f"forum-post-{item['post_id']}",
        "post_id": item["post_id"],
        "title": item["title"],
        "url": item["url"],
    }
