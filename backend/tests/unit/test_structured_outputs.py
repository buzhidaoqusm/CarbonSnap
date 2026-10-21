"""The four JSON-returning calls on the chat path ask for a schema and keep to it.

Against a fake provider on a local port, so the request body each call sends
is checked as sent.
"""

from __future__ import annotations

import json

import pytest

from app.services.ai import case_resolver, intent_router, memory_extractor
from app.services.ai import recycling_analysis_service as recycling
from tests.support import fake_provider

pytestmark = pytest.mark.real_llm_client


@pytest.fixture
def provider(override_settings):
    fake = fake_provider.start("structured-model")
    override_settings(
        llm_provider="openrouter",
        openrouter_base_url=fake.base_url,
        openrouter_api_key="key",
        openrouter_model="structured-model",
        llm_fallback_provider="",
        ai_llm_max_retries=0,
    )
    yield fake
    fake_provider.stop(fake)


ROUTER_REPLY = {
    "intent": "recycling_analysis",
    "follow_up_type": None,
    "confidence": 0.9,
    "possible_preference_signal": False,
    "needs_clarification": False,
    "clarification_question": None,
    "clarification_options": [],
}


def _route(message: str = "Can I recycle a pizza box?") -> dict:
    return intent_router.classify_intent_detailed(
        message=message,
        image_data_url=None,
        recent_history=[],
        case_summaries=[],
        conversation_state=None,
        prompt_memory=None,
        allow_business_fallback=True,
    )


def _schema(request) -> dict:
    response_format = request.payload["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    return response_format["json_schema"]["schema"]


def test_the_router_asks_for_a_strict_schema(provider):
    provider.reply = json.dumps(ROUTER_REPLY)

    detail = _route()

    schema = _schema(provider.requests[0])
    assert sorted(schema["properties"]["intent"]["enum"]) == sorted(intent_router.INTENTS)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    assert detail["router_failure_reason"] is None
    assert detail["result"]["intent"] == "recycling_analysis"


def test_a_reply_outside_the_schema_is_named_as_such(provider):
    provider.reply = json.dumps({**ROUTER_REPLY, "intent": "shopping"})

    detail = _route()

    assert detail["router_failure_reason"] == "schema_mismatch"
    assert detail["used_fallback"] is True


def test_json_inside_prose_is_no_longer_dug_out(provider):
    # The regex that pulled the first {...} out of a reply is gone: with a
    # schema the provider returns the object alone, and anything else is a
    # failure to see rather than one to paper over.
    provider.reply = "Sure! " + json.dumps(ROUTER_REPLY)

    detail = _route()

    assert detail["router_failure_reason"] == "invalid_json"


def test_the_resolver_asks_for_a_strict_schema(provider):
    provider.reply = json.dumps(
        {
            "target_case_id": 12,
            "confidence": 0.9,
            "needs_clarification": False,
            "clarification_question": None,
            "clarification_options": [],
        }
    )

    detail = case_resolver.resolve_target_case_detailed(
        message="the battery one",
        recent_history=[],
        case_summaries=[
            {"case_id": 11, "predicted_item": "jar"},
            {"case_id": 12, "predicted_item": "battery"},
        ],
        allow_heuristic_fallback=False,
    )

    _schema(provider.requests[0])
    assert detail["result"]["target_case_id"] == 12


def test_a_response_style_reaches_memory_in_the_shape_memory_reads(provider):
    # Regression: the prompt said only "value: object", so the model returned
    # {"style": "concise"} while memory_service reads value["value"]; the
    # preference was stored and never applied.
    provider.reply = json.dumps(
        {
            "is_explicit_preference": True,
            "memory_candidates": [
                {
                    "memory_type": "response_style",
                    "memory_key": "response_style",
                    "style": "concise",
                    "enabled": None,
                    "topic": None,
                    "item_type": None,
                    "preferred_method": None,
                }
            ],
        }
    )

    detail = memory_extractor.extract_explicit_memory_candidates_detailed(
        "Keep your answers short.", allow_heuristic_fallback=False
    )

    _schema(provider.requests[0])
    assert detail["candidates"] == [
        {
            "memory_type": "response_style",
            "memory_key": "response_style",
            "value": {"value": "concise"},
        }
    ]


def test_a_stage1_weight_with_units_falls_back_instead_of_crashing(provider):
    # Regression: the normalizer ran float() on the reply outside the call's
    # try, so "0.5 kg" raised out of the stream instead of using the fallback.
    provider.reply = json.dumps(
        {
            "waste_type": "Glass jar",
            "confidence": 0.9,
            "estimated_weight_kg": "0.5 kg",
            "recycle_suggestions": ["Rinse it."],
            "needs_nearby_search": True,
            "forum_references": [],
        }
    )

    payload = recycling._analyze_stage1(message="What is this?", image_data_url=None)

    assert payload["waste_type"] == "Mixed recyclable waste"
