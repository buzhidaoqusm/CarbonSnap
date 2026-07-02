from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select

from app.extensions.db import db
from app.models.ai import AIMessageDecision


def create_message_decision(
    *,
    conversation_id: int,
    user_message_id: int,
    intent: str,
    follow_up_type: str | None = None,
    target_case_id: int | None = None,
    confidence: float | None = None,
    needs_clarification: bool = False,
    decision_payload: dict[str, Any],
    engine_version: str,
) -> AIMessageDecision:
    decision = AIMessageDecision(
        conversation_id=conversation_id,
        user_message_id=user_message_id,
        intent=intent,
        follow_up_type=follow_up_type,
        target_case_id=target_case_id,
        confidence=confidence,
        needs_clarification=needs_clarification,
        decision_json=json.dumps(decision_payload, ensure_ascii=False),
        engine_version=engine_version,
    )
    db.session.add(decision)
    db.session.commit()
    return decision


def list_message_decisions_for_conversation(conversation_id: int) -> list[AIMessageDecision]:
    decisions = db.session.scalars(
        select(AIMessageDecision)
        .where(AIMessageDecision.conversation_id == conversation_id)
        .order_by(AIMessageDecision.id.asc())
    ).all()
    return list(decisions)


def get_latest_message_decision_for_message(message_id: int) -> AIMessageDecision | None:
    return db.session.scalar(
        select(AIMessageDecision)
        .where(AIMessageDecision.user_message_id == message_id)
        .order_by(AIMessageDecision.id.desc())
    )
