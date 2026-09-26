"""Flask glue for app.core.config.Settings.

Parsing and defaults live in app/core/config.py. This module copies them into
app.config under the old key names, so Flask extensions (SQLAlchemy, JWT) and
code not yet moved to get_settings() keep working while P1 migrates callers.
"""

from datetime import timedelta
from typing import Any

from flask import Flask

from app.core.config import Settings, get_settings


def load_app_settings(app: Flask) -> None:
    settings = get_settings()

    # Directories are created at startup, not while parsing settings.
    settings.forum_rag_faiss_dir.mkdir(parents=True, exist_ok=True)
    settings.upload_root.mkdir(parents=True, exist_ok=True)

    app.config.update(
        SQLALCHEMY_DATABASE_URI=settings.database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        JWT_SECRET_KEY=settings.jwt_secret_key,
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(days=7),
    )
    app.config.update(legacy_config(settings))


def legacy_config(settings: Settings) -> dict[str, Any]:
    """Application settings under their old app.config key names.

    Flask-extension keys (SQLALCHEMY_*, JWT_*) are not included: they are read
    once when the extensions initialise, and tests adjust them separately.
    """
    return {
        # LLM provider
        "LLM_PROVIDER": settings.llm_provider,
        "OPENROUTER_API_KEY": settings.openrouter_api_key,
        "OPENROUTER_BASE_URL": settings.openrouter_base_url,
        "OPENROUTER_MODEL": settings.openrouter_model,
        "OPENROUTER_SITE_URL": settings.openrouter_site_url,
        "OPENROUTER_SITE_NAME": settings.openrouter_site_name,
        "QWEN_API_KEY": settings.qwen_api_key,
        "QWEN_BASE_URL": settings.qwen_base_url,
        "QWEN_MODEL": settings.qwen_model,
        "AI_LLM_TIMEOUT_SECONDS": settings.ai_llm_timeout_seconds,
        "AI_LLM_AUX_TIMEOUT_SECONDS": settings.ai_llm_aux_timeout_seconds,
        "AI_LLM_MAX_RETRIES": settings.ai_llm_max_retries,
        # OpenStreetMap
        "OSM_NOMINATIM_URL": settings.osm_nominatim_url,
        "OSM_OVERPASS_URL": settings.osm_overpass_url,
        "OSM_OVERPASS_FALLBACK_URLS": settings.osm_overpass_fallback_urls,
        "OSM_OVERPASS_TIMEOUT_SECONDS": settings.osm_overpass_timeout_seconds,
        "OSM_OVERPASS_CONNECT_TIMEOUT_SECONDS": settings.osm_overpass_connect_timeout_seconds,
        "OSM_OVERPASS_MAX_ATTEMPTS_PER_ENDPOINT": settings.osm_overpass_max_attempts_per_endpoint,
        "OSM_OVERPASS_RETRY_BACKOFF_MS": settings.osm_overpass_retry_backoff_ms,
        "OSM_USER_AGENT": settings.osm_user_agent,
        "AI_OSM_RECYCLING_TAGS": settings.ai_osm_recycling_tags,
        # Location and map search
        "AI_BROWSER_LOCATION_TTL_MINUTES": settings.ai_browser_location_ttl_minutes,
        "AI_MANUAL_LOCATION_TTL_HOURS": settings.ai_manual_location_ttl_hours,
        "AI_MAP_SEARCH_RADIUS_METERS": settings.ai_map_search_radius_meters,
        "AI_MAP_SEARCH_LIMIT": settings.ai_map_search_limit,
        # Conversation, decision engine and agents
        "AI_SHORT_TERM_MEMORY_TURNS": settings.ai_short_term_memory_turns,
        "AI_DECISION_ENGINE_VERSION": settings.ai_decision_engine_version,
        "AI_DECISION_CONFIDENCE_THRESHOLD": settings.ai_decision_confidence_threshold,
        "AI_DECISION_ENGINE_MODE": settings.ai_decision_engine_mode,
        "AI_TRACE_ENABLED": settings.ai_trace_enabled,
        "AI_TRACE_INCLUDE_RETRIEVAL_EXCERPTS": settings.ai_trace_include_retrieval_excerpts,
        "AI_GRAPH_AGENT_ENABLED": settings.ai_graph_agent_enabled,
        "AI_TOOL_CALLING_AGENT_ENABLED": settings.ai_tool_calling_agent_enabled,
        "AI_TOOL_SELECTION_MODE": settings.ai_tool_selection_mode,
        "AI_TOOL_SELECTION_SHADOW_LOG": settings.ai_tool_selection_shadow_log,
        "AI_AGENT_MAX_ITERATIONS": settings.ai_agent_max_iterations,
        "AI_PROMPTOPS_SHADOW_ENABLED": settings.ai_promptops_shadow_enabled,
        "AI_DEMO_REPLAY_ENABLED": settings.ai_demo_replay_enabled,
        "AI_DEMO_REPLAY_CHUNK_SIZE": settings.ai_demo_replay_chunk_size,
        "AI_EMISSION_FACTORS": settings.ai_emission_factors,
        # Forum RAG / graph
        "FORUM_RAG_CHUNK_TARGET_TOKENS": settings.forum_rag_chunk_target_tokens,
        "FORUM_RAG_CHUNK_OVERLAP_TOKENS": settings.forum_rag_chunk_overlap_tokens,
        "FORUM_RAG_KEYWORD_TOP_K": settings.forum_rag_keyword_top_k,
        "FORUM_RAG_VECTOR_TOP_K": settings.forum_rag_vector_top_k,
        "FORUM_RAG_FINAL_TOP_K": settings.forum_rag_final_top_k,
        "FORUM_RAG_FAISS_DIR": str(settings.forum_rag_faiss_dir),
        "FORUM_RAG_EMBEDDING_MODEL": settings.forum_rag_embedding_model,
        "AI_NEO4J_GRAPHRAG_ENABLED": settings.ai_neo4j_graphrag_enabled,
        "NEO4J_URI": settings.neo4j_uri,
        "NEO4J_USERNAME": settings.neo4j_username,
        "NEO4J_PASSWORD": settings.neo4j_password,
        # Uploads
        "UPLOAD_ROOT": str(settings.upload_root),
        "UPLOAD_URL_PREFIX": settings.upload_url_prefix,
    }
