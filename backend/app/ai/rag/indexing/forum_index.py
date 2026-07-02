from __future__ import annotations

import json
import math
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from flask import current_app, has_app_context

from app.services.ai.openrouter_service import embed_texts

try:  # pragma: no cover - exercised implicitly when faiss is installed
    import faiss  # type: ignore
    import numpy as np  # type: ignore

    _FAISS_AVAILABLE = True
except Exception:  # pragma: no cover - fallback path is covered in tests
    faiss = None
    np = None
    _FAISS_AVAILABLE = False


class ForumRagIndexError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ForumRagChunkRecord:
    chunk_id: str
    post_id: int
    chunk_index: int
    section_title: str | None
    chunk_version: int
    chunk_text: str


@dataclass(frozen=True, slots=True)
class ForumRagSearchHit(ForumRagChunkRecord):
    score: float
    numeric_id: int


@dataclass(slots=True)
class _StoredChunk:
    chunk_id: str
    numeric_id: int
    post_id: int
    chunk_index: int
    section_title: str | None
    chunk_version: int
    chunk_text: str
    vector: list[float]

    def to_manifest_item(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["vector"] = list(self.vector)
        return payload

    @classmethod
    def from_manifest_item(cls, item: dict[str, Any]) -> "_StoredChunk":
        vector = item.get("vector")
        if not isinstance(vector, list):
            raise ForumRagIndexError("Manifest item is missing an embedding vector.")

        return cls(
            chunk_id=str(item["chunk_id"]),
            numeric_id=int(item["numeric_id"]),
            post_id=int(item["post_id"]),
            chunk_index=int(item["chunk_index"]),
            section_title=item.get("section_title"),
            chunk_version=int(item["chunk_version"]),
            chunk_text=str(item["chunk_text"]),
            vector=[float(value) for value in vector],
        )

    def to_search_hit(self, *, score: float) -> ForumRagSearchHit:
        return ForumRagSearchHit(
            chunk_id=self.chunk_id,
            post_id=self.post_id,
            chunk_index=self.chunk_index,
            section_title=self.section_title,
            chunk_version=self.chunk_version,
            chunk_text=self.chunk_text,
            score=score,
            numeric_id=self.numeric_id,
        )


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_vector(vector: Sequence[float]) -> list[float]:
    values = [float(value) for value in vector]
    if not values:
        raise ValueError("Embedding vector must not be empty.")

    if any(not math.isfinite(value) for value in values):
        raise ValueError("Embedding vector contains non-finite values.")

    norm = math.sqrt(sum(value * value for value in values))
    if norm <= 0.0:
        raise ValueError("Embedding vector norm must be greater than zero.")

    return [value / norm for value in values]


def _dot_product(left: Sequence[float], right: Sequence[float]) -> float:
    return float(sum(float(a) * float(b) for a, b in zip(left, right)))


def _resolve_storage_dir(storage_dir: str | Path | None) -> Path:
    if storage_dir is not None:
        return Path(storage_dir)

    if has_app_context():
        configured = current_app.config.get("FORUM_RAG_FAISS_DIR")
        if configured:
            return Path(str(configured))

    return Path.cwd() / "data" / "faiss"


def _resolve_embedding_model(embedding_model: str | None) -> str | None:
    if embedding_model:
        return embedding_model

    if has_app_context():
        configured = str(current_app.config.get("FORUM_RAG_EMBEDDING_MODEL", "") or "").strip()
        if configured:
            return configured

    return None


def _default_embedder(embedding_model: str | None) -> Callable[[list[str]], list[list[float]]]:
    def _embed(texts: list[str]) -> list[list[float]]:
        return embed_texts(texts, model=embedding_model or "text-embedding-v3")

    return _embed


class _VectorBackend:
    def __init__(self, index_path: Path) -> None:
        self._index_path = index_path
        self._records_by_numeric_id: dict[int, _StoredChunk] = {}
        self._dimension: int | None = None
        self._faiss_index: Any = None

    def rebuild(self, records: Iterable[_StoredChunk]) -> None:
        ordered_records = list(records)
        self._records_by_numeric_id = {record.numeric_id: record for record in ordered_records}

        if ordered_records:
            dimensions = {len(record.vector) for record in ordered_records}
            if len(dimensions) != 1:
                raise ForumRagIndexError("Stored chunk vectors do not share the same dimension.")
            self._dimension = dimensions.pop()
        else:
            self._dimension = None

        if _FAISS_AVAILABLE and ordered_records:
            self._faiss_index = self._build_faiss_index(ordered_records)
        else:
            self._faiss_index = None

    def search(self, query_vector: Sequence[float], top_k: int) -> list[tuple[int, float]]:
        if top_k <= 0:
            return []

        normalized_query = _normalize_vector(query_vector)
        if self._dimension is not None and len(normalized_query) != self._dimension:
            raise ForumRagIndexError(
                "Query embedding dimension does not match the stored forum RAG index."
            )

        if self._faiss_index is not None:
            return self._search_with_faiss(normalized_query, top_k)
        return self._search_with_python(normalized_query, top_k)

    def save(self) -> None:
        if not _FAISS_AVAILABLE:
            return

        if self._faiss_index is None:
            if self._index_path.exists():
                self._index_path.unlink()
            return

        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._faiss_index, str(self._index_path))

    def _build_faiss_index(self, records: list[_StoredChunk]) -> Any:
        if not _FAISS_AVAILABLE:
            raise ForumRagIndexError("FAISS is not available in this environment.")

        dimension = len(records[0].vector)
        index = faiss.IndexIDMap2(faiss.IndexFlatIP(dimension))

        vectors = []
        ids = []
        for record in records:
            if len(record.vector) != dimension:
                raise ForumRagIndexError("Stored chunk vectors do not share the same dimension.")
            vectors.append(record.vector)
            ids.append(record.numeric_id)

        if vectors:
            index.add_with_ids(
                np.asarray(vectors, dtype="float32"),
                np.asarray(ids, dtype="int64"),
            )
        return index

    def _search_with_faiss(self, query_vector: list[float], top_k: int) -> list[tuple[int, float]]:
        if self._faiss_index is None:
            return []

        scores, ids = self._faiss_index.search(
            np.asarray([query_vector], dtype="float32"),
            top_k,
        )
        results: list[tuple[int, float]] = []
        for numeric_id, score in zip(ids[0], scores[0]):
            if int(numeric_id) == -1:
                continue
            results.append((int(numeric_id), float(score)))
        return results

    def _search_with_python(self, query_vector: list[float], top_k: int) -> list[tuple[int, float]]:
        scored = [
            (numeric_id, _dot_product(query_vector, record.vector))
            for numeric_id, record in self._records_by_numeric_id.items()
        ]
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]


class ForumRagIndex:
    def __init__(
        self,
        *,
        storage_dir: str | Path | None = None,
        index_name: str = "forum_rag",
        embedder: Callable[[list[str]], list[list[float]]] | None = None,
        embedding_model: str | None = None,
    ) -> None:
        self._lock = threading.RLock()
        self._storage_dir = _resolve_storage_dir(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._index_name = index_name
        self._index_path = self._storage_dir / f"{index_name}.faiss"
        self._manifest_path = self._storage_dir / f"{index_name}.json"
        self._embedding_model = _resolve_embedding_model(embedding_model)
        self._embedder = embedder or _default_embedder(self._embedding_model)

        self._records_by_chunk_id: dict[str, _StoredChunk] = {}
        self._records_by_numeric_id: dict[int, str] = {}
        self._next_numeric_id = 1
        self._dimension: int | None = None
        self._backend = _VectorBackend(self._index_path)

        self._load_manifest()
        if embedder is None:
            self._embedder = _default_embedder(self._embedding_model)
        self._refresh_backend()

    @classmethod
    def from_app_config(
        cls,
        *,
        index_name: str = "forum_rag",
        embedder: Callable[[list[str]], list[list[float]]] | None = None,
    ) -> "ForumRagIndex":
        return cls(index_name=index_name, embedder=embedder)

    def upsert(self, chunks: Iterable[ForumRagChunkRecord]) -> list[ForumRagChunkRecord]:
        normalized_chunks = [self._normalize_chunk(chunk) for chunk in chunks]
        if not normalized_chunks:
            return []

        vectors = self._embedder([chunk.chunk_text for chunk in normalized_chunks])
        if len(vectors) != len(normalized_chunks):
            raise ForumRagIndexError("Embedding provider returned an unexpected vector count.")

        with self._lock:
            for chunk, vector in zip(normalized_chunks, vectors):
                normalized_vector = _normalize_vector(vector)
                existing = self._records_by_chunk_id.get(chunk.chunk_id)
                numeric_id = existing.numeric_id if existing else self._next_numeric_id

                stored = _StoredChunk(
                    chunk_id=chunk.chunk_id,
                    numeric_id=numeric_id,
                    post_id=chunk.post_id,
                    chunk_index=chunk.chunk_index,
                    section_title=chunk.section_title,
                    chunk_version=chunk.chunk_version,
                    chunk_text=chunk.chunk_text,
                    vector=normalized_vector,
                )
                self._records_by_chunk_id[chunk.chunk_id] = stored
                self._records_by_numeric_id[numeric_id] = chunk.chunk_id
                if not existing:
                    self._next_numeric_id += 1

            self._dimension = len(vectors[0])
            self._refresh_backend()
            self._persist_manifest()

        return normalized_chunks

    def delete(self, chunk_ids: Iterable[str]) -> int:
        candidate_ids = [str(chunk_id).strip() for chunk_id in chunk_ids if str(chunk_id).strip()]
        if not candidate_ids:
            return 0

        removed = 0
        with self._lock:
            for chunk_id in candidate_ids:
                stored = self._records_by_chunk_id.pop(chunk_id, None)
                if stored is None:
                    continue
                self._records_by_numeric_id.pop(stored.numeric_id, None)
                removed += 1

            if removed:
                if not self._records_by_chunk_id:
                    self._dimension = None
                self._refresh_backend()
                self._persist_manifest()

        return removed

    def search(
        self,
        query: str | Sequence[float],
        *,
        top_k: int = 5,
    ) -> list[ForumRagSearchHit]:
        if isinstance(query, str):
            query_text = _normalize_text(query)
            if not query_text:
                raise ValueError("Search query must not be blank.")
            query_vector = self._embedder([query_text])[0]
        else:
            query_vector = list(query)

        with self._lock:
            matches = self._backend.search(query_vector, top_k)
            hits: list[ForumRagSearchHit] = []
            for numeric_id, score in matches:
                chunk_id = self._records_by_numeric_id.get(numeric_id)
                if chunk_id is None:
                    continue
                stored = self._records_by_chunk_id.get(chunk_id)
                if stored is None:
                    continue
                hits.append(stored.to_search_hit(score=score))
            return hits

    def rebuild(self) -> None:
        with self._lock:
            self._refresh_backend()
            self._persist_manifest()

    def list_chunks(self) -> list[ForumRagChunkRecord]:
        with self._lock:
            return [
                ForumRagChunkRecord(
                    chunk_id=stored.chunk_id,
                    post_id=stored.post_id,
                    chunk_index=stored.chunk_index,
                    section_title=stored.section_title,
                    chunk_version=stored.chunk_version,
                    chunk_text=stored.chunk_text,
                )
                for stored in sorted(
                    self._records_by_chunk_id.values(),
                    key=lambda item: (item.post_id, item.chunk_version, item.chunk_index, item.numeric_id),
                )
            ]

    def _normalize_chunk(self, chunk: ForumRagChunkRecord) -> ForumRagChunkRecord:
        normalized_chunk_id = _normalize_text(chunk.chunk_id)
        if not normalized_chunk_id:
            raise ValueError("chunk_id must not be blank.")

        normalized_text = _normalize_text(chunk.chunk_text)
        if not normalized_text:
            raise ValueError("chunk_text must not be blank.")

        section_title = _normalize_text(chunk.section_title) if chunk.section_title else None
        if not section_title:
            section_title = None

        return ForumRagChunkRecord(
            chunk_id=normalized_chunk_id,
            post_id=int(chunk.post_id),
            chunk_index=int(chunk.chunk_index),
            section_title=section_title,
            chunk_version=int(chunk.chunk_version),
            chunk_text=normalized_text,
        )

    def _load_manifest(self) -> None:
        if not self._manifest_path.exists():
            return

        try:
            raw_payload = json.loads(self._manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive guard
            raise ForumRagIndexError(f"Unable to read forum RAG manifest: {exc}") from exc

        if not isinstance(raw_payload, dict):
            raise ForumRagIndexError("Forum RAG manifest must contain a JSON object.")

        records = raw_payload.get("records", [])
        if not isinstance(records, list):
            raise ForumRagIndexError("Forum RAG manifest records must be a list.")

        next_numeric_id = raw_payload.get("next_numeric_id")
        if next_numeric_id is not None:
            self._next_numeric_id = max(1, int(next_numeric_id))

        if raw_payload.get("embedding_model"):
            self._embedding_model = str(raw_payload.get("embedding_model")).strip() or self._embedding_model

        for item in records:
            if not isinstance(item, dict):
                raise ForumRagIndexError("Forum RAG manifest contains an invalid record entry.")
            stored = _StoredChunk.from_manifest_item(item)
            self._records_by_chunk_id[stored.chunk_id] = stored
            self._records_by_numeric_id[stored.numeric_id] = stored.chunk_id

        dimension = raw_payload.get("dimension")
        if dimension is not None:
            self._dimension = int(dimension)
        elif self._records_by_chunk_id:
            self._dimension = len(next(iter(self._records_by_chunk_id.values())).vector)

    def _persist_manifest(self) -> None:
        payload = {
            "schema_version": 1,
            "index_name": self._index_name,
            "backend": "faiss" if _FAISS_AVAILABLE else "python",
            "embedding_model": self._embedding_model,
            "dimension": self._dimension,
            "next_numeric_id": self._next_numeric_id,
            "records": [
                stored.to_manifest_item()
                for stored in sorted(
                    self._records_by_chunk_id.values(),
                    key=lambda item: (item.numeric_id, item.chunk_id),
                )
            ],
        }
        self._manifest_path.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )

    def _refresh_backend(self) -> None:
        ordered_records = sorted(
            self._records_by_chunk_id.values(),
            key=lambda item: (item.numeric_id, item.chunk_id),
        )
        self._backend.rebuild(ordered_records)
        self._backend.save()


def build_forum_rag_index(
    *,
    storage_dir: str | Path | None = None,
    index_name: str = "forum_rag",
    embedder: Callable[[list[str]], list[list[float]]] | None = None,
) -> ForumRagIndex:
    return ForumRagIndex(storage_dir=storage_dir, index_name=index_name, embedder=embedder)
