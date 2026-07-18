import os
from datetime import timedelta
from json import loads as json_loads
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask


def load_app_settings(app: Flask) -> None:
    backend_root = Path(__file__).resolve().parents[2]
    env_path = backend_root / ".env"

    load_dotenv(dotenv_path=env_path, override=False)

    # Database
    _db_default = f"sqlite:///{backend_root.parent / 'data' / 'carbonsnap.db'}"
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", _db_default)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # JWT — override JWT_SECRET_KEY in production via .env
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=7)

    app.config["LLM_PROVIDER"] = os.getenv("LLM_PROVIDER", "openrouter").strip().lower() or "openrouter"
    app.config["OPENROUTER_API_KEY"] = os.getenv("OPENROUTER_API_KEY", "").strip()
    app.config["OPENROUTER_BASE_URL"] = os.getenv(
        "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
    ).strip()
    app.config["OPENROUTER_MODEL"] = os.getenv(
        "OPENROUTER_MODEL", "openai/gpt-5.2"
    ).strip()
    app.config["OPENROUTER_SITE_URL"] = os.getenv("OPENROUTER_SITE_URL", "").strip()
    app.config["OPENROUTER_SITE_NAME"] = os.getenv(
        "OPENROUTER_SITE_NAME", "CarbonSnap"
    ).strip()
    app.config["QWEN_API_KEY"] = os.getenv("QWEN_API_KEY", "").strip()
    app.config["QWEN_BASE_URL"] = os.getenv(
        "QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ).strip()
    app.config["QWEN_MODEL"] = os.getenv(
        "QWEN_MODEL", "qwen-plus"
    ).strip()
    app.config["OSM_NOMINATIM_URL"] = os.getenv(
        "OSM_NOMINATIM_URL", "https://nominatim.openstreetmap.org"
    ).strip()
    app.config["OSM_OVERPASS_URL"] = os.getenv(
        "OSM_OVERPASS_URL", "https://overpass-api.de/api/interpreter"
    ).strip()
    app.config["OSM_OVERPASS_FALLBACK_URLS"] = _load_overpass_fallback_urls(
        primary_url=app.config["OSM_OVERPASS_URL"]
    )
    app.config["OSM_OVERPASS_TIMEOUT_SECONDS"] = float(
        os.getenv("OSM_OVERPASS_TIMEOUT_SECONDS", "30").strip()
    )
    app.config["OSM_OVERPASS_CONNECT_TIMEOUT_SECONDS"] = float(
        os.getenv("OSM_OVERPASS_CONNECT_TIMEOUT_SECONDS", "8").strip()
    )
    app.config["OSM_OVERPASS_MAX_ATTEMPTS_PER_ENDPOINT"] = int(
        os.getenv("OSM_OVERPASS_MAX_ATTEMPTS_PER_ENDPOINT", "2").strip()
    )
    app.config["OSM_OVERPASS_RETRY_BACKOFF_MS"] = int(
        os.getenv("OSM_OVERPASS_RETRY_BACKOFF_MS", "400").strip()
    )
    app.config["OSM_USER_AGENT"] = os.getenv(
        "OSM_USER_AGENT", "CarbonSnap/0.1 (development)"
    ).strip()
    app.config["AI_BROWSER_LOCATION_TTL_MINUTES"] = int(
        os.getenv("AI_BROWSER_LOCATION_TTL_MINUTES", "60").strip()
    )
    app.config["AI_MANUAL_LOCATION_TTL_HOURS"] = int(
        os.getenv("AI_MANUAL_LOCATION_TTL_HOURS", "24").strip()
    )
    app.config["AI_MAP_SEARCH_RADIUS_METERS"] = int(
        os.getenv("AI_MAP_SEARCH_RADIUS_METERS", "3000").strip()
    )
    app.config["AI_MAP_SEARCH_LIMIT"] = int(
        os.getenv("AI_MAP_SEARCH_LIMIT", "12").strip()
    )
    app.config["AI_SHORT_TERM_MEMORY_TURNS"] = int(
        os.getenv("AI_SHORT_TERM_MEMORY_TURNS", "10").strip()
    )
    app.config["FORUM_RAG_CHUNK_TARGET_TOKENS"] = int(
        os.getenv("FORUM_RAG_CHUNK_TARGET_TOKENS", "420").strip()
    )
    app.config["FORUM_RAG_CHUNK_OVERLAP_TOKENS"] = int(
        os.getenv("FORUM_RAG_CHUNK_OVERLAP_TOKENS", "70").strip()
    )
    app.config["FORUM_RAG_KEYWORD_TOP_K"] = int(
        os.getenv("FORUM_RAG_KEYWORD_TOP_K", "8").strip()
    )
    app.config["FORUM_RAG_VECTOR_TOP_K"] = int(
        os.getenv("FORUM_RAG_VECTOR_TOP_K", "8").strip()
    )
    app.config["FORUM_RAG_FINAL_TOP_K"] = int(
        os.getenv("FORUM_RAG_FINAL_TOP_K", "4").strip()
    )
    forum_rag_faiss_dir = Path(
        os.getenv("FORUM_RAG_FAISS_DIR", backend_root.parent / "data" / "faiss")
    )
    forum_rag_faiss_dir.mkdir(parents=True, exist_ok=True)
    app.config["FORUM_RAG_FAISS_DIR"] = str(forum_rag_faiss_dir)
    app.config["FORUM_RAG_EMBEDDING_MODEL"] = os.getenv(
        "FORUM_RAG_EMBEDDING_MODEL", "text-embedding-v3"
    ).strip()
    app.config["AI_DECISION_ENGINE_VERSION"] = (
        os.getenv("AI_DECISION_ENGINE_VERSION", "decision-engine-v2").strip()
        or "decision-engine-v2"
    )
    app.config["AI_DECISION_CONFIDENCE_THRESHOLD"] = float(
        os.getenv("AI_DECISION_CONFIDENCE_THRESHOLD", "0.65").strip()
    )
    app.config["AI_DECISION_ENGINE_MODE"] = (
        os.getenv("AI_DECISION_ENGINE_MODE", "llm_first").strip().lower() or "llm_first"
    )
    app.config["AI_TRACE_ENABLED"] = _get_bool_env("AI_TRACE_ENABLED", True)
    app.config["AI_GRAPH_AGENT_ENABLED"] = _get_bool_env("AI_GRAPH_AGENT_ENABLED", False)
    app.config["AI_TOOL_CALLING_AGENT_ENABLED"] = _get_bool_env(
        "AI_TOOL_CALLING_AGENT_ENABLED", False
    )
    app.config["AI_AGENT_MAX_ITERATIONS"] = int(
        os.getenv("AI_AGENT_MAX_ITERATIONS", "4").strip() or "4"
    )
    app.config["AI_LLM_TIMEOUT_SECONDS"] = float(
        os.getenv("AI_LLM_TIMEOUT_SECONDS", "60").strip() or "60"
    )
    app.config["AI_NEO4J_GRAPHRAG_ENABLED"] = _get_bool_env(
        "AI_NEO4J_GRAPHRAG_ENABLED", False
    )
    app.config["NEO4J_URI"] = os.getenv("NEO4J_URI", "").strip()
    app.config["NEO4J_USERNAME"] = os.getenv("NEO4J_USERNAME", "").strip()
    app.config["NEO4J_PASSWORD"] = os.getenv("NEO4J_PASSWORD", "").strip()
    app.config["AI_PROMPTOPS_SHADOW_ENABLED"] = _get_bool_env(
        "AI_PROMPTOPS_SHADOW_ENABLED", False
    )
    app.config["AI_TRACE_INCLUDE_RETRIEVAL_EXCERPTS"] = _get_bool_env(
        "AI_TRACE_INCLUDE_RETRIEVAL_EXCERPTS", True
    )
    app.config["AI_DEMO_REPLAY_ENABLED"] = os.getenv(
        "AI_DEMO_REPLAY_ENABLED", ""
    ).strip().lower() in {"1", "true", "yes", "on"}
    app.config["AI_DEMO_REPLAY_CHUNK_SIZE"] = int(
        os.getenv("AI_DEMO_REPLAY_CHUNK_SIZE", "120").strip()
    )
    upload_root = Path(os.getenv("UPLOAD_ROOT", backend_root.parent / "data" / "uploads"))
    upload_root.mkdir(parents=True, exist_ok=True)
    app.config["UPLOAD_ROOT"] = str(upload_root)
    app.config["UPLOAD_URL_PREFIX"] = os.getenv("UPLOAD_URL_PREFIX", "/api/uploads").strip() or "/api/uploads"
    app.config["AI_EMISSION_FACTORS"] = _load_emission_factors()
    app.config["AI_OSM_RECYCLING_TAGS"] = _load_osm_recycling_tags()


def _get_bool_env(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _load_emission_factors() -> dict[str, float]:
    raw_value = os.getenv("AI_EMISSION_FACTORS_JSON", "").strip()
    if raw_value:
        try:
            parsed = json_loads(raw_value)
            return {str(key).lower(): float(value) for key, value in parsed.items()}
        except Exception:
            pass

    return {
        "plastic bottle": 1.5,
        "plastic": 1.4,
        "paper": 1.0,
        "cardboard": 0.8,
        "glass": 0.5,
        "metal can": 2.1,
        "metal": 1.9,
        "aluminum can": 2.5,
        "electronics": 3.2,
        "battery": 3.8,
        "default": 1.0,
    }


def _load_osm_recycling_tags() -> list[dict[str, str]]:
    raw_value = os.getenv("AI_OSM_RECYCLING_TAGS_JSON", "").strip()
    if raw_value:
        try:
            parsed = json_loads(raw_value)
            return [
                {"key": str(item["key"]), "value": str(item["value"])}
                for item in parsed
                if isinstance(item, dict) and item.get("key") and item.get("value")
            ]
        except Exception:
            pass

    return [
        {"key": "amenity", "value": "recycling"},
        {"key": "recycling_type", "value": "centre"},
        {"key": "recycling_type", "value": "container"},
        {"key": "amenity", "value": "waste_disposal"},
        {"key": "amenity", "value": "waste_transfer_station"},
    ]


def _load_overpass_fallback_urls(*, primary_url: str) -> list[str]:
    raw_value = os.getenv("OSM_OVERPASS_FALLBACK_URLS_JSON", "").strip()
    if raw_value:
        try:
            parsed = json_loads(raw_value)
            if isinstance(parsed, list):
                return [
                    str(item).strip()
                    for item in parsed
                    if str(item).strip() and str(item).strip() != primary_url
                ]
        except Exception:
            pass

    defaults = [
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
    ]
    return [url for url in defaults if url != primary_url]
