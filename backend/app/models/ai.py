from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str | None] = mapped_column(String(256))
    # active | awaiting_location | completed | archived
    status: Mapped[str] = mapped_column(String(32), default="active")
    # none | location_permission | manual_area_input
    current_pending_action: Mapped[str] = mapped_column(String(32), default="none")
    # Stores session-scoped chat context such as location permission/cache state.
    session_context_json: Mapped[str | None] = mapped_column(Text)
    last_message_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class WasteAnalysisRecord(Base):
    __tablename__ = "waste_analysis_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("ai_conversations.id"))
    # These two close foreign key cycles (recycling_cases and
    # recycling_audit_attempts point back here), so they are added after the
    # tables exist and dropped before them, as migration d71c6e1f9a21 does.
    # use_alter needs a name for DROP CONSTRAINT.
    recycling_case_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "recycling_cases.id",
            use_alter=True,
            name="fk_waste_analysis_records_recycling_case_id_recycling_cases",
        )
    )
    approved_audit_attempt_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "recycling_audit_attempts.id",
            use_alter=True,
            name="fk_waste_analysis_records_approved_audit_attempt_id",
        )
    )
    image_url: Mapped[str | None] = mapped_column(String(256))
    waste_type: Mapped[str | None] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column(default=0.0)
    estimated_weight_kg: Mapped[float] = mapped_column(default=0.0)
    co2_saved_kg: Mapped[float] = mapped_column(default=0.0)
    carbon_points: Mapped[int] = mapped_column(default=0)
    # Raw AI response stored as JSON text, kept for debugging.
    raw_ai_response_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))


class RecyclingCase(Base):
    __tablename__ = "recycling_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    conversation_id: Mapped[int] = mapped_column(ForeignKey("ai_conversations.id"))
    # Links back to the assistant/user message that created this recycling case.
    origin_message_id: Mapped[int] = mapped_column(ForeignKey("ai_messages.id"))
    waste_type_predicted: Mapped[str] = mapped_column(String(64))
    confidence: Mapped[float] = mapped_column(default=0.0)
    estimated_weight_kg: Mapped[float] = mapped_column(default=0.0)
    expected_co2_saved_kg: Mapped[float] = mapped_column(default=0.0)
    expected_carbon_points: Mapped[float] = mapped_column(default=0.0)
    # pending_audit | audit_failed | audit_passed | cancelled
    status: Mapped[str] = mapped_column(String(32), default="pending_audit")
    latest_audit_attempt_no: Mapped[int] = mapped_column(default=0)
    approved_analysis_id: Mapped[int | None] = mapped_column(
        ForeignKey("waste_analysis_records.id")
    )
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class RecyclingAuditAttempt(Base):
    __tablename__ = "recycling_audit_attempts"
    __table_args__ = (
        UniqueConstraint(
            "recycling_case_id",
            "attempt_no",
            name="uq_recycling_audit_attempt_case_attempt",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    recycling_case_id: Mapped[int] = mapped_column(ForeignKey("recycling_cases.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    conversation_id: Mapped[int] = mapped_column(ForeignKey("ai_conversations.id"))
    audit_image_url: Mapped[str] = mapped_column(String(256))
    attempt_no: Mapped[int] = mapped_column()
    # passed | failed | unclear
    audit_result: Mapped[str] = mapped_column(String(16))
    auditor_confidence: Mapped[float] = mapped_column(default=0.0)
    audit_reason: Mapped[str | None] = mapped_column(Text)
    audit_response_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))


class AIMessage(Base):
    __tablename__ = "ai_messages"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "sequence_no",
            name="uq_ai_messages_conversation_sequence",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("ai_conversations.id"))
    # user | assistant | tool | system
    role: Mapped[str] = mapped_column(String(16))
    # text | image | analysis_result | recycling_case | audit_result | tool_call | tool_result | user_action
    message_type: Mapped[str] = mapped_column(String(32), default="text")
    content_text: Mapped[str | None] = mapped_column(Text)
    content_json: Mapped[str | None] = mapped_column(Text)
    related_analysis_id: Mapped[int | None] = mapped_column(ForeignKey("waste_analysis_records.id"))
    sequence_no: Mapped[int] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))


class AIMessageDecision(Base):
    __tablename__ = "ai_message_decisions"
    __table_args__ = (
        Index("ix_ai_message_decisions_conversation_id", "conversation_id"),
        Index("ix_ai_message_decisions_user_message_id", "user_message_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("ai_conversations.id"))
    user_message_id: Mapped[int] = mapped_column(ForeignKey("ai_messages.id"))
    intent: Mapped[str] = mapped_column(String(32))
    follow_up_type: Mapped[str | None] = mapped_column(String(32))
    target_case_id: Mapped[int | None] = mapped_column(ForeignKey("recycling_cases.id"))
    confidence: Mapped[float | None] = mapped_column()
    needs_clarification: Mapped[bool] = mapped_column(default=False)
    decision_json: Mapped[str] = mapped_column(Text)
    engine_version: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
