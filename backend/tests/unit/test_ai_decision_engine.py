from __future__ import annotations

import pytest

from app.services.ai import ai_decision_engine


def _context(
    *,
    recent_history: list[dict] | None = None,
    case_summaries: list[dict] | None = None,
    conversation_state: dict | None = None,
) -> dict:
    return {
        "recent_history": recent_history or [],
        "case_summaries": case_summaries or [],
        "working_memory": {
            "conversation_state": conversation_state
            or {"status": "active", "current_pending_action": "none"}
        },
    }


def _router_detail(
    *,
    intent: str = "general_chat",
    follow_up_type: str | None = None,
    confidence: float = 0.82,
    needs_clarification: bool = False,
    clarification_question: str | None = None,
    clarification_options: list[dict] | None = None,
    used_fallback: bool = False,
    fallback_mode: str | None = None,
    router_failure_reason: str | None = None,
    raw_router_payload: str = "{}",
) -> dict:
    return {
        "result": {
            "intent": intent,
            "follow_up_type": follow_up_type,
            "confidence": confidence,
            "possible_preference_signal": False,
            "needs_clarification": needs_clarification,
            "clarification_question": clarification_question,
            "clarification_options": clarification_options or [],
        },
        "router_failure_reason": router_failure_reason,
        "raw_router_payload": raw_router_payload,
        "used_fallback": used_fallback,
        "fallback_mode": fallback_mode,
    }


def _resolver_detail(
    *,
    target_case_id: int | None = None,
    confidence: float = 0.0,
    needs_clarification: bool = False,
    clarification_question: str | None = None,
    clarification_options: list[dict] | None = None,
    used_fallback: bool = False,
    fallback_mode: str | None = None,
    resolver_failure_reason: str | None = None,
    raw_resolver_payload: str = "{}",
) -> dict:
    return {
        "result": {
            "target_case_id": target_case_id,
            "confidence": confidence,
            "needs_clarification": needs_clarification,
            "clarification_question": clarification_question,
            "clarification_options": clarification_options or [],
        },
        "resolver_failure_reason": resolver_failure_reason,
        "raw_resolver_payload": raw_resolver_payload,
        "used_fallback": used_fallback,
        "fallback_mode": fallback_mode,
    }


def _extractor_detail(
    *,
    candidates: list[dict] | None = None,
    extractor_failure_reason: str | None = None,
    raw_extractor_payload: str = "[]",
    used_fallback: bool = False,
    fallback_mode: str | None = None,
) -> dict:
    return {
        "candidates": candidates or [],
        "extractor_failure_reason": extractor_failure_reason,
        "raw_extractor_payload": raw_extractor_payload,
        "used_fallback": used_fallback,
        "fallback_mode": fallback_mode,
    }


def _case(case_id: int, predicted_item: str, stage: str) -> dict:
    return {
        "case_id": case_id,
        "predicted_item": predicted_item,
        "current_stage": stage,
        "status": stage,
    }


class TestDecisionModes:
    def test_llm_first_mode_uses_safe_default_and_disables_business_fallback(
        self, monkeypatch, app
    ):
        app.config["AI_DECISION_ENGINE_MODE"] = "llm_first"

        captured: dict[str, bool] = {}
        monkeypatch.setattr(ai_decision_engine, "get_prompt_memory_summary", lambda user_id: {})
        monkeypatch.setattr(
            ai_decision_engine,
            "build_context_bundle",
            lambda **kwargs: _context(case_summaries=[_case(2, "plastic bottle", "audit_passed")]),
        )

        def fake_router(**kwargs):
            captured["router_allow_business_fallback"] = kwargs["allow_business_fallback"]
            return _router_detail(
                intent="general_chat",
                confidence=0.0,
                used_fallback=True,
                fallback_mode="safe_default",
                router_failure_reason="invalid_intent",
                raw_router_payload='{"intent":"bad_intent"}',
            )

        def fake_extractor(*args, **kwargs):
            captured["extractor_allow_heuristic_fallback"] = kwargs["allow_heuristic_fallback"]
            return _extractor_detail()

        monkeypatch.setattr(ai_decision_engine, "classify_intent_detailed", fake_router)
        monkeypatch.setattr(
            ai_decision_engine,
            "resolve_target_case_detailed",
            lambda **kwargs: pytest.fail("resolver should not be called for general chat"),
        )
        monkeypatch.setattr(
            ai_decision_engine,
            "extract_explicit_memory_candidates_detailed",
            fake_extractor,
        )

        decision = ai_decision_engine.decide_message(
            user_id=1,
            conversation_id=2,
            message="What did I just recycle?",
            image_data_url=None,
        )

        assert decision["decision_mode"] == "llm_first"
        assert decision["intent"] == "general_chat"
        assert decision["router_failure_reason"] == "invalid_intent"
        assert decision["router_fallback_mode"] == "safe_default"
        assert captured == {
            "router_allow_business_fallback": False,
            "extractor_allow_heuristic_fallback": False,
        }

    def test_compat_mode_uses_primary_pipeline_without_shadow_metadata(self, monkeypatch, app):
        app.config["AI_DECISION_ENGINE_MODE"] = "compat"

        captured: dict[str, bool] = {}
        monkeypatch.setattr(ai_decision_engine, "get_prompt_memory_summary", lambda user_id: {})
        monkeypatch.setattr(
            ai_decision_engine,
            "build_context_bundle",
            lambda **kwargs: _context(case_summaries=[_case(7, "battery", "awaiting_location")]),
        )

        def fake_router(**kwargs):
            captured["router_allow_business_fallback"] = kwargs["allow_business_fallback"]
            return _router_detail(
                intent="recycling_follow_up",
                follow_up_type="nearby_search",
                confidence=0.61,
                used_fallback=True,
                fallback_mode="business_fallback",
                router_failure_reason="invalid_json:ValueError",
                raw_router_payload="not-json",
            )

        def fake_resolver(**kwargs):
            captured["resolver_allow_heuristic_fallback"] = kwargs["allow_heuristic_fallback"]
            return _resolver_detail(
                target_case_id=7,
                confidence=0.91,
                used_fallback=True,
                fallback_mode="heuristic_fallback",
                resolver_failure_reason="invalid_resolver_payload",
                raw_resolver_payload="not-json",
            )

        def fake_extractor(*args, **kwargs):
            captured["extractor_allow_heuristic_fallback"] = kwargs["allow_heuristic_fallback"]
            return _extractor_detail(
                candidates=[
                    {
                        "memory_type": "recycling_preference",
                        "memory_key": "allow_manual_area_input",
                        "value": {"value": True},
                    }
                ],
                used_fallback=True,
                fallback_mode="heuristic_fallback",
            )

        monkeypatch.setattr(ai_decision_engine, "classify_intent_detailed", fake_router)
        monkeypatch.setattr(ai_decision_engine, "resolve_target_case_detailed", fake_resolver)
        monkeypatch.setattr(
            ai_decision_engine,
            "extract_explicit_memory_candidates_detailed",
            fake_extractor,
        )

        decision = ai_decision_engine.decide_message(
            user_id=1,
            conversation_id=2,
            message="Can you find a nearby drop-off point for those batteries?",
            image_data_url=None,
        )

        assert decision["decision_mode"] == "compat"
        assert decision["pipeline_label"] == "compat"
        assert decision["intent"] == "recycling_follow_up"
        assert decision["target_case_id"] == 7
        assert decision["should_retrieve_forum"] is True
        assert "shadow_decision" not in decision
        assert decision["extractor_fallback_mode"] == "heuristic_fallback"
        assert captured == {
            "router_allow_business_fallback": True,
            "resolver_allow_heuristic_fallback": True,
            "extractor_allow_heuristic_fallback": True,
        }

    def test_shadow_mode_persists_shadow_decision_metadata(self, monkeypatch, app):
        app.config["AI_DECISION_ENGINE_MODE"] = "shadow"

        monkeypatch.setattr(ai_decision_engine, "get_prompt_memory_summary", lambda user_id: {})
        monkeypatch.setattr(
            ai_decision_engine,
            "build_context_bundle",
            lambda **kwargs: _context(),
        )

        calls: list[bool] = []

        def fake_router(**kwargs):
            allow_business_fallback = kwargs["allow_business_fallback"]
            calls.append(allow_business_fallback)
            if allow_business_fallback:
                return _router_detail(
                    intent="recycling_analysis",
                    confidence=0.61,
                    used_fallback=True,
                    fallback_mode="business_fallback",
                    router_failure_reason="invalid_json:ValueError",
                    raw_router_payload="not-json",
                )
            return _router_detail(
                intent="general_chat",
                confidence=0.0,
                used_fallback=True,
                fallback_mode="safe_default",
                router_failure_reason="invalid_json:ValueError",
                raw_router_payload="not-json",
            )

        monkeypatch.setattr(ai_decision_engine, "classify_intent_detailed", fake_router)
        monkeypatch.setattr(
            ai_decision_engine,
            "extract_explicit_memory_candidates_detailed",
            lambda *args, **kwargs: _extractor_detail(),
        )

        decision = ai_decision_engine.decide_message(
            user_id=1,
            conversation_id=2,
            message="How do I recycle this bottle?",
            image_data_url=None,
        )

        assert decision["decision_mode"] == "shadow"
        assert decision["pipeline_label"] == "compat"
        assert decision["intent"] == "recycling_analysis"
        assert decision["shadow_decision"]["intent"] == "general_chat"
        assert decision["shadow_decision"]["pipeline_label"] == "shadow"
        assert "context" not in decision["shadow_decision"]
        assert "prompt_memory" not in decision["shadow_decision"]
        assert calls == [True, False]

    def test_invalid_mode_falls_back_to_llm_first(self, monkeypatch, app):
        app.config["AI_DECISION_ENGINE_MODE"] = "rollbackish"

        def fake_pipeline(**kwargs):
            return {
                "engine_version": "decision-engine-v2",
                "pipeline_label": kwargs["label"],
                "intent": "general_chat",
            }

        monkeypatch.setattr(ai_decision_engine, "_run_decision_pipeline", fake_pipeline)

        decision = ai_decision_engine.decide_message(
            user_id=1,
            conversation_id=2,
            message="Thanks.",
            image_data_url=None,
        )

        assert decision["decision_mode"] == "llm_first"
        assert decision["pipeline_label"] == "llm_first"


class TestDecisionPipeline:
    def test_follow_up_uses_resolver_and_keeps_target_case_when_confident(self, monkeypatch, app):
        app.config["AI_DECISION_ENGINE_MODE"] = "llm_first"
        app.config["AI_DECISION_CONFIDENCE_THRESHOLD"] = 0.65

        monkeypatch.setattr(ai_decision_engine, "get_prompt_memory_summary", lambda user_id: {})
        monkeypatch.setattr(
            ai_decision_engine,
            "build_context_bundle",
            lambda **kwargs: _context(
                case_summaries=[
                    _case(1, "plastic bottle", "analysis_ready"),
                    _case(2, "battery", "awaiting_location"),
                ]
            ),
        )
        monkeypatch.setattr(
            ai_decision_engine,
            "classify_intent_detailed",
            lambda **kwargs: _router_detail(
                intent="recycling_follow_up",
                follow_up_type="nearby_search",
                confidence=0.94,
            ),
        )
        monkeypatch.setattr(
            ai_decision_engine,
            "resolve_target_case_detailed",
            lambda **kwargs: _resolver_detail(target_case_id=2, confidence=0.85),
        )
        monkeypatch.setattr(
            ai_decision_engine,
            "extract_explicit_memory_candidates_detailed",
            lambda *args, **kwargs: _extractor_detail(),
        )

        decision = ai_decision_engine.decide_message(
            user_id=1,
            conversation_id=2,
            message="Continue with the battery one.",
            image_data_url=None,
        )

        assert decision["intent"] == "recycling_follow_up"
        assert decision["target_case_id"] == 2
        assert decision["resolution_confidence"] == 0.85
        assert decision["needs_clarification"] is False
        assert decision["should_retrieve_forum"] is True

    def test_resolver_clarification_overrides_router_clarification_fields(self, monkeypatch, app):
        app.config["AI_DECISION_ENGINE_MODE"] = "llm_first"

        monkeypatch.setattr(ai_decision_engine, "get_prompt_memory_summary", lambda user_id: {})
        monkeypatch.setattr(
            ai_decision_engine,
            "build_context_bundle",
            lambda **kwargs: _context(
                case_summaries=[
                    _case(1, "plastic bottle", "analysis_ready"),
                    _case(2, "battery", "audit_failed"),
                ]
            ),
        )
        monkeypatch.setattr(
            ai_decision_engine,
            "classify_intent_detailed",
            lambda **kwargs: _router_detail(
                intent="recycling_follow_up",
                follow_up_type="guidance_follow_up",
                confidence=0.88,
                needs_clarification=True,
                clarification_question="Which earlier task do you mean?",
                clarification_options=[
                    {"label": "Earlier task", "reply_text": "That earlier task."}
                ],
            ),
        )
        monkeypatch.setattr(
            ai_decision_engine,
            "resolve_target_case_detailed",
            lambda **kwargs: _resolver_detail(
                target_case_id=None,
                confidence=0.0,
                needs_clarification=True,
                clarification_question="Which item do you want to continue?",
                clarification_options=[
                    {"label": "Plastic bottle", "reply_text": "I mean the bottle."},
                    {"label": "Battery", "reply_text": "I mean the batteries."},
                ],
            ),
        )
        monkeypatch.setattr(
            ai_decision_engine,
            "extract_explicit_memory_candidates_detailed",
            lambda *args, **kwargs: _extractor_detail(),
        )

        decision = ai_decision_engine.decide_message(
            user_id=1,
            conversation_id=2,
            message="Can you help with the recycling task from earlier?",
            image_data_url=None,
        )

        assert decision["needs_clarification"] is True
        assert decision["target_case_id"] is None
        assert decision["clarification_question"] == "Which item do you want to continue?"
        assert decision["clarification_options"] == [
            {"label": "Plastic bottle", "reply_text": "I mean the bottle."},
            {"label": "Battery", "reply_text": "I mean the batteries."},
        ]

    def test_multi_case_low_confidence_follow_up_forces_clarification(self, monkeypatch, app):
        app.config["AI_DECISION_ENGINE_MODE"] = "llm_first"
        app.config["AI_DECISION_CONFIDENCE_THRESHOLD"] = 0.7
        app.config["AI_DECISION_ENGINE_VERSION"] = "decision-engine-test"

        monkeypatch.setattr(ai_decision_engine, "get_prompt_memory_summary", lambda user_id: {})
        monkeypatch.setattr(
            ai_decision_engine,
            "build_context_bundle",
            lambda **kwargs: _context(
                case_summaries=[
                    _case(1, "plastic bottle", "analysis_ready"),
                    _case(2, "battery", "awaiting_location"),
                ]
            ),
        )
        monkeypatch.setattr(
            ai_decision_engine,
            "classify_intent_detailed",
            lambda **kwargs: _router_detail(
                intent="recycling_follow_up",
                follow_up_type="nearby_search",
                confidence=0.94,
            ),
        )
        monkeypatch.setattr(
            ai_decision_engine,
            "resolve_target_case_detailed",
            lambda **kwargs: _resolver_detail(target_case_id=2, confidence=0.55),
        )
        monkeypatch.setattr(
            ai_decision_engine,
            "extract_explicit_memory_candidates_detailed",
            lambda *args, **kwargs: _extractor_detail(),
        )

        decision = ai_decision_engine.decide_message(
            user_id=1,
            conversation_id=2,
            message="Continue that one.",
            image_data_url=None,
        )

        assert decision["engine_version"] == "decision-engine-test"
        assert decision["needs_clarification"] is True
        assert decision["target_case_id"] is None
        assert len(decision["clarification_options"]) == 2

    def test_confidence_equal_to_threshold_keeps_target_case(self, monkeypatch, app):
        app.config["AI_DECISION_ENGINE_MODE"] = "llm_first"
        app.config["AI_DECISION_CONFIDENCE_THRESHOLD"] = 0.65

        monkeypatch.setattr(ai_decision_engine, "get_prompt_memory_summary", lambda user_id: {})
        monkeypatch.setattr(
            ai_decision_engine,
            "build_context_bundle",
            lambda **kwargs: _context(
                case_summaries=[
                    _case(1, "plastic bottle", "analysis_ready"),
                    _case(2, "battery", "awaiting_location"),
                ]
            ),
        )
        monkeypatch.setattr(
            ai_decision_engine,
            "classify_intent_detailed",
            lambda **kwargs: _router_detail(
                intent="recycling_follow_up",
                follow_up_type="guidance_follow_up",
                confidence=0.91,
            ),
        )
        monkeypatch.setattr(
            ai_decision_engine,
            "resolve_target_case_detailed",
            lambda **kwargs: _resolver_detail(target_case_id=1, confidence=0.65),
        )
        monkeypatch.setattr(
            ai_decision_engine,
            "extract_explicit_memory_candidates_detailed",
            lambda *args, **kwargs: _extractor_detail(),
        )

        decision = ai_decision_engine.decide_message(
            user_id=1,
            conversation_id=2,
            message="Do you have other recycling suggestions for that bottle?",
            image_data_url=None,
        )

        assert decision["target_case_id"] == 1
        assert decision["needs_clarification"] is False


class TestForumRetrieval:
    def test_recycling_intents_enable_forum_retrieval(self, monkeypatch, app):
        app.config["AI_DECISION_ENGINE_MODE"] = "llm_first"

        monkeypatch.setattr(ai_decision_engine, "get_prompt_memory_summary", lambda user_id: {})
        monkeypatch.setattr(
            ai_decision_engine,
            "build_context_bundle",
            lambda **kwargs: _context(),
        )
        monkeypatch.setattr(
            ai_decision_engine,
            "classify_intent_detailed",
            lambda **kwargs: _router_detail(intent="recycling_analysis", confidence=0.88),
        )
        monkeypatch.setattr(
            ai_decision_engine,
            "extract_explicit_memory_candidates_detailed",
            lambda *args, **kwargs: _extractor_detail(),
        )

        decision = ai_decision_engine.decide_message(
            user_id=1,
            conversation_id=2,
            message="How should I recycle this Oriental Leaf jasmine tea bottle?",
            image_data_url="/api/uploads/seed-ai/oriental-leaf-jasmine-tea-bottle.jpg",
        )

        assert decision["should_retrieve_forum"] is True
        assert decision["forum_retrieval_reason"] == "recycling_priority:analysis"
        assert decision["forum_citation_policy"] == "mixed_strict_for_facts"
        assert decision["trace"]["schema_version"] == "graph-agent-trace-v1"
        assert decision["trace"]["router"]["intent"] == "recycling_analysis"
        assert decision["trace"]["retrieval"]["forum"]["enabled"] is True
        assert decision["trace"]["retrieval"]["forum"]["reason"] == "recycling_priority:analysis"
        assert decision["trace"]["prompt_versions"]["router"] == "router-v1"
        assert decision["trace"]["prompt_versions"]["decision_engine"] == decision["engine_version"]

    def test_general_chat_query_hint_triggers_forum_retrieval(self, monkeypatch, app):
        monkeypatch.setattr(ai_decision_engine, "get_prompt_memory_summary", lambda user_id: {})
        monkeypatch.setattr(
            ai_decision_engine,
            "build_context_bundle",
            lambda **kwargs: _context(),
        )
        monkeypatch.setattr(
            ai_decision_engine,
            "classify_intent_detailed",
            lambda **kwargs: _router_detail(intent="general_chat", confidence=0.76),
        )
        monkeypatch.setattr(
            ai_decision_engine,
            "extract_explicit_memory_candidates_detailed",
            lambda *args, **kwargs: _extractor_detail(),
        )

        decision = ai_decision_engine.decide_message(
            user_id=1,
            conversation_id=2,
            message="Forum tips for sorting used batteries safely?",
            image_data_url=None,
        )

        assert decision["intent"] == "general_chat"
        assert decision["should_retrieve_forum"] is True
        assert decision["forum_retrieval_reason"] == "general_chat_hint"

    def test_general_chat_people_question_triggers_forum_retrieval(self, monkeypatch, app):
        monkeypatch.setattr(ai_decision_engine, "get_prompt_memory_summary", lambda user_id: {})
        monkeypatch.setattr(
            ai_decision_engine,
            "build_context_bundle",
            lambda **kwargs: _context(),
        )
        monkeypatch.setattr(
            ai_decision_engine,
            "classify_intent_detailed",
            lambda **kwargs: _router_detail(intent="general_chat", confidence=0.71),
        )
        monkeypatch.setattr(
            ai_decision_engine,
            "extract_explicit_memory_candidates_detailed",
            lambda *args, **kwargs: _extractor_detail(),
        )

        decision = ai_decision_engine.decide_message(
            user_id=1,
            conversation_id=2,
            message="Has anyone shared a good battery drawer reset routine?",
            image_data_url=None,
        )

        assert decision["should_retrieve_forum"] is True
        assert decision["forum_retrieval_reason"] == "general_chat_hint"

    def test_image_with_relevant_history_triggers_forum_retrieval(self, monkeypatch, app):
        monkeypatch.setattr(ai_decision_engine, "get_prompt_memory_summary", lambda user_id: {})
        monkeypatch.setattr(
            ai_decision_engine,
            "build_context_bundle",
            lambda **kwargs: _context(
                recent_history=[
                    {
                        "role": "assistant",
                        "content": "You could reuse sturdy glass jars as simple spice containers.",
                    }
                ]
            ),
        )
        monkeypatch.setattr(
            ai_decision_engine,
            "classify_intent_detailed",
            lambda **kwargs: _router_detail(intent="general_chat", confidence=0.69),
        )
        monkeypatch.setattr(
            ai_decision_engine,
            "extract_explicit_memory_candidates_detailed",
            lambda *args, **kwargs: _extractor_detail(),
        )

        decision = ai_decision_engine.decide_message(
            user_id=1,
            conversation_id=2,
            message="What else could I do with jars like this?",
            image_data_url="/api/uploads/seed-ai/example-jars.png",
        )

        assert decision["should_retrieve_forum"] is True
        assert decision["forum_retrieval_reason"] == "general_chat_hint"

    def test_general_chat_without_signals_does_not_trigger_forum_retrieval(self, monkeypatch, app):
        monkeypatch.setattr(ai_decision_engine, "get_prompt_memory_summary", lambda user_id: {})
        monkeypatch.setattr(
            ai_decision_engine,
            "build_context_bundle",
            lambda **kwargs: _context(),
        )
        monkeypatch.setattr(
            ai_decision_engine,
            "classify_intent_detailed",
            lambda **kwargs: _router_detail(intent="general_chat", confidence=0.75),
        )
        monkeypatch.setattr(
            ai_decision_engine,
            "extract_explicit_memory_candidates_detailed",
            lambda *args, **kwargs: _extractor_detail(),
        )

        decision = ai_decision_engine.decide_message(
            user_id=1,
            conversation_id=2,
            message="Thanks, that helps a lot.",
            image_data_url=None,
        )

        assert decision["should_retrieve_forum"] is False
        assert decision["forum_retrieval_reason"] == "not_triggered"


class TestPersistenceAndHelpers:
    def test_persist_message_decision_strips_internal_fields_and_prefers_resolution_confidence(
        self, monkeypatch
    ):
        captured: dict = {}

        def fake_create_message_decision(**kwargs):
            captured.update(kwargs)
            return kwargs

        monkeypatch.setattr(
            ai_decision_engine.message_decision_repository,
            "create_message_decision",
            fake_create_message_decision,
        )

        decision = {
            "engine_version": "decision-engine-v2",
            "intent": "recycling_follow_up",
            "follow_up_type": "nearby_search",
            "target_case_id": 9,
            "confidence": 0.21,
            "resolution_confidence": 0.83,
            "needs_clarification": True,
            "context": {"recent_history": []},
            "prompt_memory": {"response_style": "concise"},
        }

        result = ai_decision_engine.persist_message_decision(
            conversation_id=4,
            user_message_id=12,
            decision=decision,
        )

        assert result == captured
        assert captured["conversation_id"] == 4
        assert captured["user_message_id"] == 12
        assert captured["confidence"] == 0.83
        assert captured["needs_clarification"] is True
        assert captured["decision_payload"] == {
            "engine_version": "decision-engine-v2",
            "intent": "recycling_follow_up",
            "follow_up_type": "nearby_search",
            "target_case_id": 9,
            "confidence": 0.21,
            "resolution_confidence": 0.83,
            "needs_clarification": True,
        }

    @pytest.mark.parametrize(
        ("configured_value", "expected"),
        [
            ("bad-value", 0.65),
            (-1, 0.0),
            (2, 1.0),
            (0.4, 0.4),
        ],
    )
    def test_get_confidence_threshold_falls_back_and_clamps(self, app, configured_value, expected):
        app.config["AI_DECISION_CONFIDENCE_THRESHOLD"] = configured_value
        assert ai_decision_engine._get_confidence_threshold() == expected

    def test_get_engine_version_returns_default_for_blank_value(self, app):
        app.config["AI_DECISION_ENGINE_VERSION"] = "   "
        assert ai_decision_engine._get_engine_version() == "decision-engine-v2"

    def test_serialize_shadow_decision_omits_internal_fields(self):
        serialized = ai_decision_engine._serialize_shadow_decision(
            {
                "intent": "general_chat",
                "pipeline_label": "shadow",
                "context": {"recent_history": []},
                "prompt_memory": {"response_style": "concise"},
                "shadow_decision": {"intent": "nested"},
            }
        )

        assert serialized == {
            "intent": "general_chat",
            "pipeline_label": "shadow",
        }
