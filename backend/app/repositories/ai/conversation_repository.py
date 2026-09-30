from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.models.ai import (
    AIConversation,
    AIMessage,
    AIMessageDecision,
    RecyclingAuditAttempt,
    RecyclingCase,
    WasteAnalysisRecord,
)
from app.models.memory import UserMemoryItem


def _utc_now() -> datetime:
    return datetime.now(UTC)


def create_conversation(
    session: Session, *, user_id: int, title: str | None = None
) -> AIConversation:
    conversation = AIConversation(
        user_id=user_id,
        title=title or "New chat",
    )
    session.add(conversation)
    session.commit()
    return conversation


def get_conversation(session: Session, conversation_id: int, user_id: int) -> AIConversation | None:
    return session.scalar(
        select(AIConversation).where(
            AIConversation.id == conversation_id,
            AIConversation.user_id == user_id,
        )
    )


def list_conversations(
    session: Session,
    user_id: int,
    limit: int = 50,
    offset: int = 0,
) -> list[AIConversation]:
    conversations = session.scalars(
        select(AIConversation)
        .where(AIConversation.user_id == user_id)
        .order_by(AIConversation.last_message_at.desc(), AIConversation.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return list(conversations)


def append_message(
    session: Session,
    *,
    conversation_id: int,
    role: str,
    message_type: str,
    content_text: str | None = None,
    content_json: str | None = None,
    related_analysis_id: int | None = None,
) -> AIMessage:
    conversation = session.get(AIConversation, conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found.")

    next_sequence_no = (
        session.scalar(
            select(AIMessage.sequence_no)
            .where(AIMessage.conversation_id == conversation_id)
            .order_by(AIMessage.sequence_no.desc())
            .limit(1)
        )
        or 0
    ) + 1

    message = AIMessage(
        conversation_id=conversation_id,
        role=role,
        message_type=message_type,
        content_text=content_text,
        content_json=content_json,
        related_analysis_id=related_analysis_id,
        sequence_no=next_sequence_no,
    )
    conversation.last_message_at = _utc_now()
    session.add(message)
    session.commit()
    return message


def list_messages(session: Session, conversation_id: int) -> list[AIMessage]:
    messages = session.scalars(
        select(AIMessage)
        .where(AIMessage.conversation_id == conversation_id)
        .order_by(AIMessage.sequence_no.asc(), AIMessage.id.asc())
    ).all()
    return list(messages)


def update_conversation_state(
    session: Session,
    conversation_id: int,
    *,
    status: str | None = None,
    current_pending_action: str | None = None,
    session_context_json: str | None = None,
    title: str | None = None,
) -> AIConversation:
    conversation = session.get(AIConversation, conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found.")

    if status is not None:
        conversation.status = status
    if current_pending_action is not None:
        conversation.current_pending_action = current_pending_action
    if session_context_json is not None:
        conversation.session_context_json = session_context_json
    if title is not None:
        conversation.title = title

    conversation.updated_at = _utc_now()
    session.commit()
    return conversation


def delete_conversation(session: Session, conversation_id: int, user_id: int) -> bool:
    conversation = get_conversation(session, conversation_id, user_id)
    if conversation is None:
        return False

    message_ids = list(
        session.scalars(select(AIMessage.id).where(AIMessage.conversation_id == conversation_id))
    )
    case_ids = list(
        session.scalars(
            select(RecyclingCase.id).where(RecyclingCase.conversation_id == conversation_id)
        )
    )
    audit_attempt_ids = list(
        session.scalars(
            select(RecyclingAuditAttempt.id).where(
                RecyclingAuditAttempt.conversation_id == conversation_id
            )
        )
    )

    if message_ids:
        session.execute(
            update(UserMemoryItem)
            .where(UserMemoryItem.source_message_id.in_(message_ids))
            .values(source_message_id=None)
        )

    session.execute(
        update(UserMemoryItem)
        .where(UserMemoryItem.conversation_id == conversation_id)
        .values(conversation_id=None)
    )

    if audit_attempt_ids:
        session.execute(
            update(WasteAnalysisRecord)
            .where(WasteAnalysisRecord.approved_audit_attempt_id.in_(audit_attempt_ids))
            .values(approved_audit_attempt_id=None)
        )

    if case_ids:
        session.execute(
            update(WasteAnalysisRecord)
            .where(WasteAnalysisRecord.recycling_case_id.in_(case_ids))
            .values(recycling_case_id=None)
        )

    session.execute(
        update(WasteAnalysisRecord)
        .where(WasteAnalysisRecord.conversation_id == conversation_id)
        .values(conversation_id=None)
    )

    session.execute(
        delete(AIMessageDecision).where(AIMessageDecision.conversation_id == conversation_id)
    )
    session.execute(
        delete(RecyclingAuditAttempt).where(
            RecyclingAuditAttempt.conversation_id == conversation_id
        )
    )
    session.execute(delete(RecyclingCase).where(RecyclingCase.conversation_id == conversation_id))
    session.execute(delete(AIMessage).where(AIMessage.conversation_id == conversation_id))
    session.delete(conversation)
    session.commit()
    return True
