"""Typed application settings, independent of Flask.

Everything configurable is declared once here, with its type and default, and
read from the environment (and ENV_FILE / backend/.env) when first needed.
Code reads it with ``get_settings().field_name`` instead of
``current_app.config.get("FIELD_NAME", default)``, which works outside a Flask
request and lets mypy catch a misspelt name.

Behaviour kept from the old os.getenv loader (tests/unit/test_config_parity.py
pins it): strings are trimmed, a blank variable means "use the default", the
three mode switches are lowercased, and malformed JSON falls back to the
built-in defaults. One deliberate difference: a boolean that is not a
recognisable true/false value is now a startup error instead of silently
becoming the default.
"""

from __future__ import annotations

import os
from functools import lru_cache
from json import loads as json_loads
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = BACKEND_ROOT.parent / "data"

DEFAULT_EMISSION_FACTORS: dict[str, float] = {
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

DEFAULT_OSM_RECYCLING_TAGS: list[dict[str, str]] = [
    {"key": "amenity", "value": "recycling"},
    {"key": "recycling_type", "value": "centre"},
    {"key": "recycling_type", "value": "container"},
    {"key": "amenity", "value": "waste_disposal"},
    {"key": "amenity", "value": "waste_transfer_station"},
]

DEFAULT_OVERPASS_FALLBACK_URLS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Field `ai_llm_timeout_seconds` is read from AI_LLM_TIMEOUT_SECONDS.
        case_sensitive=False,
        # AI_LLM_TIMEOUT_SECONDS="" means "not set", i.e. the default.
        env_ignore_empty=True,
        str_strip_whitespace=True,
        # Settings are fixed at startup; nothing may change them at runtime.
        frozen=True,
        extra="ignore",
    )

    # --- Database / auth ------------------------------------------------------
    database_url: str = f"sqlite:///{DATA_ROOT / 'carbonsnap.db'}"
    jwt_secret_key: str = "dev-secret-change-in-production"

    # --- LLM provider ----------------------------------------------------------
    llm_provider: str = "openrouter"
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "openai/gpt-5.2"
    openrouter_site_url: str = ""
    openrouter_site_name: str = "CarbonSnap"
    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen-plus"
    ai_llm_timeout_seconds: float = 60
    # Router, memory extraction and title calls: short, never retried, and each
    # has a fallback. Keeps a hanging provider from outliving the worker.
    ai_llm_aux_timeout_seconds: float = 15
    # Provider-side retries for transient failures (429/5xx/timeouts), handled
    # by the OpenAI SDK. Tests set 0 so a blocked call fails immediately.
    ai_llm_max_retries: int = 2

    # --- OpenStreetMap -----------------------------------------------------------
    osm_nominatim_url: str = "https://nominatim.openstreetmap.org"
    osm_overpass_url: str = "https://overpass-api.de/api/interpreter"
    osm_overpass_fallback_urls_json: str = ""
    osm_overpass_timeout_seconds: float = 30
    osm_overpass_connect_timeout_seconds: float = 8
    osm_overpass_max_attempts_per_endpoint: int = 2
    osm_overpass_retry_backoff_ms: int = 400
    osm_user_agent: str = "CarbonSnap/0.1 (development)"
    ai_osm_recycling_tags_json: str = ""

    # --- Location and map search -----------------------------------------------
    ai_browser_location_ttl_minutes: int = 60
    ai_manual_location_ttl_hours: int = 24
    ai_map_search_radius_meters: int = 3000
    ai_map_search_limit: int = 12

    # --- Conversation, decision engine and agents --------------------------------
    ai_short_term_memory_turns: int = 10
    ai_decision_engine_version: str = "decision-engine-v2"
    ai_decision_confidence_threshold: float = 0.65
    ai_decision_engine_mode: str = "llm_first"
    ai_trace_enabled: bool = True
    ai_trace_include_retrieval_excerpts: bool = True
    ai_graph_agent_enabled: bool = False
    ai_tool_calling_agent_enabled: bool = False
    # Tool-selection rollout mode: "rule" (v1, default) | "model" (v2, A6) |
    # "shadow" (serve v1, compare against v2's selection, A7). Empty falls back
    # to the legacy AI_TOOL_CALLING_AGENT_ENABLED boolean (true -> "model").
    ai_tool_selection_mode: str = ""
    # JSONL sink for rule-vs-model tool-selection comparisons. Empty (default)
    # disables logging so no file is written unless explicitly opted in.
    ai_tool_selection_shadow_log: str = ""
    ai_agent_max_iterations: int = 4
    ai_promptops_shadow_enabled: bool = False
    ai_demo_replay_enabled: bool = False
    ai_demo_replay_chunk_size: int = 120
    ai_emission_factors_json: str = ""

    # --- Forum RAG / graph ------------------------------------------------------
    forum_rag_chunk_target_tokens: int = 420
    forum_rag_chunk_overlap_tokens: int = 70
    forum_rag_keyword_top_k: int = 8
    forum_rag_vector_top_k: int = 8
    forum_rag_final_top_k: int = 4
    forum_rag_faiss_dir: Path = DATA_ROOT / "faiss"
    forum_rag_embedding_model: str = "text-embedding-v3"
    ai_neo4j_graphrag_enabled: bool = False
    neo4j_uri: str = ""
    neo4j_username: str = ""
    neo4j_password: str = ""

    # --- Uploads ---------------------------------------------------------------
    upload_root: Path = DATA_ROOT / "uploads"
    upload_url_prefix: str = "/api/uploads"

    @field_validator("llm_provider", "ai_decision_engine_mode", "ai_tool_selection_mode")
    @classmethod
    def _lowercase(cls, value: str) -> str:
        return value.lower()

    # JSON-valued variables are kept as raw strings and parsed leniently here:
    # malformed input falls back to the defaults, as it always has.

    @property
    def ai_emission_factors(self) -> dict[str, float]:
        try:
            parsed = json_loads(self.ai_emission_factors_json)
            return {str(key).lower(): float(value) for key, value in parsed.items()}
        except Exception:
            return dict(DEFAULT_EMISSION_FACTORS)

    @property
    def ai_osm_recycling_tags(self) -> list[dict[str, str]]:
        try:
            parsed = json_loads(self.ai_osm_recycling_tags_json)
            return [
                {"key": str(item["key"]), "value": str(item["value"])}
                for item in parsed
                if isinstance(item, dict) and item.get("key") and item.get("value")
            ]
        except Exception:
            return [dict(tag) for tag in DEFAULT_OSM_RECYCLING_TAGS]

    @property
    def osm_overpass_fallback_urls(self) -> list[str]:
        primary = self.osm_overpass_url
        try:
            parsed = json_loads(self.osm_overpass_fallback_urls_json)
            if isinstance(parsed, list):
                return [
                    str(item).strip()
                    for item in parsed
                    if str(item).strip() and str(item).strip() != primary
                ]
        except Exception:
            pass
        return [url for url in DEFAULT_OVERPASS_FALLBACK_URLS if url != primary]


def _env_file() -> Path:
    # ENV_FILE lets tests, containers and CI point somewhere else (or at an
    # empty file) instead of picking up a developer's local .env.
    return Path(os.getenv("ENV_FILE", BACKEND_ROOT / ".env"))


@lru_cache
def get_settings() -> Settings:
    """Parse the environment once; every later call returns the same object."""
    return Settings(_env_file=_env_file(), _env_file_encoding="utf-8")  # type: ignore[call-arg]
