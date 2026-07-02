"""Integration tests for completion-photo recycling audit APIs."""

from __future__ import annotations

import json
import uuid

from sqlalchemy import func, select
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app.extensions.db import db
from app.models.ai import AIConversation, RecyclingCase, WasteAnalysisRecord
from app.models.ledger import Transaction
from app.models.user import User
from app.services.ai import recycling_audit_service, recycling_analysis_service

_VALID_IMAGE_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7Z0vcAAAAASUVORK5CYII="
)


def _post_json(client, url, data, headers=None, buffered=False):
    return client.post(
        url,
        data=json.dumps(data),
        content_type="application/json",
        headers=headers,
        buffered=buffered,
    )


def _extract_sse_payloads(response) -> list[dict]:
    body = response.get_data(as_text=True)
    data_lines = [line for line in body.splitlines() if line.startswith("data: ")]
    return [json.loads(line.removeprefix("data: ")) for line in data_lines]


def _make_auth_headers(client, *, username: str = "audit-user", email: str = "audit@example.com", points: int = 0):
    unique_suffix = uuid.uuid4().hex[:8]
    with client.application.app_context():
        db.session.rollback()
        db.create_all()
        user = User(
            username=f"{username}_{unique_suffix}",
            email=f"{unique_suffix}_{email}",
            password_hash=generate_password_hash("password123"),
            current_points=points,
        )
        db.session.add(user)
        db.session.commit()
        token = create_access_token(identity=str(user.id))
        return user.id, {"Authorization": f"Bearer {token}"}


def _seed_pending_case(client, headers, monkeypatch):
    session_id = f"audit-integration-session-{uuid.uuid4().hex[:8]}"
    monkeypatch.setattr(
        recycling_analysis_service,
        "_analyze_stage1",
        lambda **kwargs: {
            "waste_type": "plastic bottle",
            "confidence": 0.91,
            "estimated_weight_kg": 0.2,
            "co2_saved_kg": 0.3,
            "carbon_points": 3.0,
            "recycle_suggestions": ["Rinse it"],
            "forum_references": [],
            "requires_location_decision": True,
        },
    )

    def fake_stream_text(**kwargs):
        yield {"type": "meta", "model": "test-model"}
        yield {"type": "delta", "content": "Stage 1 summary"}
        yield {"type": "done", "finish_reason": "stop"}

    monkeypatch.setattr(recycling_analysis_service, "stream_text", fake_stream_text)

    response = _post_json(
        client,
        "/api/ai/analyze-image",
        {
            "message": "Please analyze this bottle",
            "image": _VALID_IMAGE_DATA_URL,
            "session_id": session_id,
        },
        headers,
        buffered=True,
    )
    payloads = _extract_sse_payloads(response)
    stage_payloads = [payload for payload in payloads if payload.get("type") == "stage_payload"]
    persisted_payload = stage_payloads[-1]["data"]
    return persisted_payload["conversation_id"], persisted_payload["recycling_case_id"]


class TestAuditApi:
    def test_failed_audit_keeps_case_retryable(self, client, monkeypatch):
        _, headers = _make_auth_headers(client)
        conversation_id, recycling_case_id = _seed_pending_case(client, headers, monkeypatch)

        monkeypatch.setattr(
            recycling_audit_service,
            "complete_json",
            lambda **kwargs: {
                "audit_result": "failed",
                "auditor_confidence": 0.31,
                "audit_reason": "The completion photo does not clearly show completion.",
            },
        )

        response = _post_json(
            client,
            "/api/ai/audit-recycling",
            {
                "conversation_id": conversation_id,
                "recycling_case_id": recycling_case_id,
                "message": "Here is my completion photo.",
                "image": _VALID_IMAGE_DATA_URL,
            },
            headers,
            buffered=True,
        )

        assert response.status_code == 200
        payloads = _extract_sse_payloads(response)
        final_payload = [payload for payload in payloads if payload.get("type") == "stage_payload"][-1]["data"]

        case = db.session.get(RecyclingCase, recycling_case_id)
        conversation = db.session.get(AIConversation, conversation_id)
        transaction_count = db.session.scalar(select(func.count(Transaction.id))) or 0

        assert final_payload["audit_result"]["audit_result"] == "failed"
        assert final_payload["retryable"] is True
        assert case.status == "audit_failed"
        assert conversation.status == "active"
        assert transaction_count == 0

    def test_passed_audit_finalizes_case_and_awards_points(self, client, monkeypatch):
        _, headers = _make_auth_headers(client)
        conversation_id, recycling_case_id = _seed_pending_case(client, headers, monkeypatch)

        monkeypatch.setattr(
            recycling_audit_service,
            "complete_json",
            lambda **kwargs: {
                "audit_result": "passed",
                "auditor_confidence": 0.98,
                "audit_reason": "The completion photo clearly shows the task was completed.",
            },
        )

        response = _post_json(
            client,
            "/api/ai/audit-recycling",
            {
                "conversation_id": conversation_id,
                "recycling_case_id": recycling_case_id,
                "message": "Here is my completion photo.",
                "image": _VALID_IMAGE_DATA_URL,
            },
            headers,
            buffered=True,
        )

        assert response.status_code == 200
        payloads = _extract_sse_payloads(response)
        final_payload = [payload for payload in payloads if payload.get("type") == "stage_payload"][-1]["data"]

        case = db.session.get(RecyclingCase, recycling_case_id)
        record = db.session.scalar(
            select(WasteAnalysisRecord).where(WasteAnalysisRecord.recycling_case_id == recycling_case_id)
        )
        transaction_count = db.session.scalar(select(func.count(Transaction.id))) or 0
        conversation = db.session.get(AIConversation, conversation_id)

        assert final_payload["audit_result"]["audit_result"] == "passed"
        assert final_payload["finalized"] is True
        assert case.status == "audit_passed"
        assert record is not None
        assert case.approved_analysis_id == record.id
        assert transaction_count == 1
        assert conversation.status == "completed"

    def test_failed_audit_can_retry_and_then_pass(self, client, monkeypatch):
        _, headers = _make_auth_headers(client)
        conversation_id, recycling_case_id = _seed_pending_case(client, headers, monkeypatch)

        audit_results = iter(
            [
                {
                    "audit_result": "failed",
                    "auditor_confidence": 0.33,
                    "audit_reason": "The first image does not clearly prove completion.",
                },
                {
                    "audit_result": "passed",
                    "auditor_confidence": 0.97,
                    "audit_reason": "The second image clearly proves completion.",
                },
            ]
        )
        monkeypatch.setattr(
            recycling_audit_service,
            "complete_json",
            lambda **kwargs: next(audit_results),
        )

        failed_response = _post_json(
            client,
            "/api/ai/audit-recycling",
            {
                "conversation_id": conversation_id,
                "recycling_case_id": recycling_case_id,
                "message": "First completion image.",
                "image": _VALID_IMAGE_DATA_URL,
            },
            headers,
            buffered=True,
        )
        assert failed_response.status_code == 200

        passed_response = _post_json(
            client,
            "/api/ai/audit-recycling",
            {
                "conversation_id": conversation_id,
                "recycling_case_id": recycling_case_id,
                "message": "Second completion image.",
                "image": _VALID_IMAGE_DATA_URL,
            },
            headers,
            buffered=True,
        )
        assert passed_response.status_code == 200

        case = db.session.get(RecyclingCase, recycling_case_id)
        record = db.session.scalar(
            select(WasteAnalysisRecord).where(WasteAnalysisRecord.recycling_case_id == recycling_case_id)
        )
        transaction_count = db.session.scalar(select(func.count(Transaction.id))) or 0

        assert case.status == "audit_passed"
        assert record is not None
        assert case.approved_analysis_id == record.id
        assert transaction_count == 1
