from __future__ import annotations

from werkzeug.security import generate_password_hash

from app.extensions.db import db
from app.models.ai import AIConversation
from app.models.user import User
from app.repositories.ai import conversation_repository, recycling_case_repository
from app.services.ai import recycling_analysis_service


def test_analyze_stage1_resolves_only_known_forum_references(monkeypatch):
    monkeypatch.setattr(
        recycling_analysis_service,
        "complete_json",
        lambda **kwargs: {
            "waste_type": "Plastic bottle",
            "confidence": 0.92,
            "estimated_weight_kg": 0.05,
            "recycle_suggestions": ["Rinse it first."],
            "needs_nearby_search": True,
            "forum_references": [
                {"title": "Bottle Sorting Guide", "url": "/forum/posts/3"},
                {"title": "Invented", "url": "/forum/posts/999"},
            ],
        },
    )

    payload = recycling_analysis_service._analyze_stage1(
        message="How should I recycle this bottle?",
        image_data_url=None,
        forum_candidates=[
            {
                "reference_id": "forum-post-3",
                "post_id": 3,
                "title": "Bottle Sorting Guide",
                "url": "/forum/posts/3",
                "excerpt": "Rinse and sort.",
                "retrieval_reason": "keyword+vector",
            }
        ],
    )

    assert payload["forum_references"] == [
        {
            "reference_id": "forum-post-3",
            "post_id": 3,
            "title": "Bottle Sorting Guide",
            "url": "/forum/posts/3",
        }
    ]


def test_analyze_stage1_includes_graph_context_in_system_prompt(monkeypatch):
    captured_request = {}

    def fake_complete_json(**kwargs):
        captured_request.update(kwargs)
        return {
            "waste_type": "Battery",
            "confidence": 0.9,
            "estimated_weight_kg": 0.04,
            "recycle_suggestions": ["Use a battery drop-off point."],
            "needs_nearby_search": True,
            "forum_references": [],
        }

    monkeypatch.setattr(recycling_analysis_service, "complete_json", fake_complete_json)

    recycling_analysis_service._analyze_stage1(
        message="How should I recycle batteries?",
        image_data_url=None,
        graph_context={
            "enabled": True,
            "entities": {"items": ["battery"]},
            "paths": [{"from": "battery", "relation": "HAS_RISK", "to": "fire hazard"}],
            "rules": [
                {
                    "id": "rule-battery-dropoff",
                    "title": "Use battery drop-off",
                    "description": "Use a battery collection point.",
                }
            ],
            "risks": [],
            "facility_types": ["household hazardous waste facility"],
        },
    )

    assert "Neo4j recycling graph evidence" in captured_request["system_prompt"]
    assert "battery --HAS_RISK--> fire hazard" in captured_request["system_prompt"]
    assert "Use battery drop-off" in captured_request["system_prompt"]


def test_selected_audit_attempt_note_uses_first_attempt_reason(app):
    with app.app_context():
        user = User(
            username="audit-user",
            email="audit-user@example.com",
            password_hash=generate_password_hash("password123"),
        )
        db.session.add(user)
        db.session.flush()

        conversation = AIConversation(
            user_id=user.id,
            title="Dual-Case Recycling Chat",
            status="completed",
            current_pending_action="none",
        )
        db.session.add(conversation)
        db.session.flush()

        origin_message = conversation_repository.append_message(
            conversation_id=conversation.id,
            role="user",
            message_type="image",
            content_text="How can I recycle this power bank?",
        )

        recycling_case = recycling_case_repository.create_recycling_case(
            user_id=user.id,
            conversation_id=conversation.id,
            origin_message_id=origin_message.id,
            waste_type_predicted="Portable Power Bank (E-waste)",
            confidence=0.94,
            estimated_weight_kg=0.21,
            expected_co2_saved_kg=0.6,
            expected_carbon_points=5,
        )

        recycling_case_repository.create_audit_attempt(
            recycling_case_id=recycling_case.id,
            user_id=user.id,
            conversation_id=conversation.id,
            audit_image_url="/uploads/attempt-1.png",
            audit_result="unclear",
            audit_reason="The power bank is in a generic recycling bin, which is not enough evidence for e-waste disposal.",
        )
        recycling_case_repository.create_audit_attempt(
            recycling_case_id=recycling_case.id,
            user_id=user.id,
            conversation_id=conversation.id,
            audit_image_url="/uploads/attempt-2.png",
            audit_result="passed",
            audit_reason="The power bank is shown at a dedicated electronics recycling collection point.",
        )

        note = recycling_analysis_service._selected_audit_attempt_note(
            case=recycling_case,
            message="Why did the first attempt fail?",
            runtime_context={
                "selected_audit_attempt": {
                    "case_id": recycling_case.id,
                    "attempt_no": 1,
                    "audit_result": "unclear",
                }
            },
        )

        assert '"attempt_no": 1' in note
        assert "generic recycling bin" in note
        assert "gently correct that" in note
