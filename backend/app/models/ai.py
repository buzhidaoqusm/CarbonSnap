from datetime import UTC, datetime

from app.extensions.db import db


class AIConversation(db.Model):
    __tablename__ = "ai_conversations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(256))
    # active | awaiting_location | completed | archived
    status = db.Column(db.String(32), nullable=False, default="active")
    # none | location_permission | manual_area_input
    current_pending_action = db.Column(db.String(32), nullable=False, default="none")
    # Stores session-scoped chat context such as location permission/cache state.
    session_context_json = db.Column(db.Text)
    last_message_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class WasteAnalysisRecord(db.Model):
    __tablename__ = "waste_analysis_records"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    conversation_id = db.Column(db.Integer, db.ForeignKey("ai_conversations.id"))
    recycling_case_id = db.Column(db.Integer, db.ForeignKey("recycling_cases.id"))
    approved_audit_attempt_id = db.Column(db.Integer, db.ForeignKey("recycling_audit_attempts.id"))
    image_url = db.Column(db.String(256))
    waste_type = db.Column(db.String(64))
    confidence = db.Column(db.Float, nullable=False, default=0.0)
    estimated_weight_kg = db.Column(db.Float, nullable=False, default=0.0)
    co2_saved_kg = db.Column(db.Float, nullable=False, default=0.0)
    carbon_points = db.Column(db.Integer, nullable=False, default=0)
    # Raw AI response stored as JSON text, kept for debugging.
    raw_ai_response_json = db.Column(db.Text)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
    )


class RecyclingCase(db.Model):
    __tablename__ = "recycling_cases"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    conversation_id = db.Column(db.Integer, db.ForeignKey("ai_conversations.id"), nullable=False)
    # Links back to the assistant/user message that created this recycling case.
    origin_message_id = db.Column(db.Integer, db.ForeignKey("ai_messages.id"), nullable=False)
    waste_type_predicted = db.Column(db.String(64), nullable=False)
    confidence = db.Column(db.Float, nullable=False, default=0.0)
    estimated_weight_kg = db.Column(db.Float, nullable=False, default=0.0)
    expected_co2_saved_kg = db.Column(db.Float, nullable=False, default=0.0)
    expected_carbon_points = db.Column(db.Float, nullable=False, default=0.0)
    # pending_audit | audit_failed | audit_passed | cancelled
    status = db.Column(db.String(32), nullable=False, default="pending_audit")
    latest_audit_attempt_no = db.Column(db.Integer, nullable=False, default=0)
    approved_analysis_id = db.Column(db.Integer, db.ForeignKey("waste_analysis_records.id"))
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class RecyclingAuditAttempt(db.Model):
    __tablename__ = "recycling_audit_attempts"
    __table_args__ = (
        db.UniqueConstraint(
            "recycling_case_id",
            "attempt_no",
            name="uq_recycling_audit_attempt_case_attempt",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    recycling_case_id = db.Column(db.Integer, db.ForeignKey("recycling_cases.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    conversation_id = db.Column(db.Integer, db.ForeignKey("ai_conversations.id"), nullable=False)
    audit_image_url = db.Column(db.String(256), nullable=False)
    attempt_no = db.Column(db.Integer, nullable=False)
    # passed | failed | unclear
    audit_result = db.Column(db.String(16), nullable=False)
    auditor_confidence = db.Column(db.Float, nullable=False, default=0.0)
    audit_reason = db.Column(db.Text)
    audit_response_json = db.Column(db.Text)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
    )


class AIMessage(db.Model):
    __tablename__ = "ai_messages"
    __table_args__ = (
        db.UniqueConstraint(
            "conversation_id",
            "sequence_no",
            name="uq_ai_messages_conversation_sequence",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("ai_conversations.id"), nullable=False)
    # user | assistant | tool | system
    role = db.Column(db.String(16), nullable=False)
    # text | image | analysis_result | recycling_case | audit_result | tool_call | tool_result | user_action
    message_type = db.Column(db.String(32), nullable=False, default="text")
    content_text = db.Column(db.Text)
    content_json = db.Column(db.Text)
    related_analysis_id = db.Column(db.Integer, db.ForeignKey("waste_analysis_records.id"))
    sequence_no = db.Column(db.Integer, nullable=False)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
    )


class AIMessageDecision(db.Model):
    __tablename__ = "ai_message_decisions"
    __table_args__ = (
        db.Index("ix_ai_message_decisions_conversation_id", "conversation_id"),
        db.Index("ix_ai_message_decisions_user_message_id", "user_message_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("ai_conversations.id"), nullable=False)
    user_message_id = db.Column(db.Integer, db.ForeignKey("ai_messages.id"), nullable=False)
    intent = db.Column(db.String(32), nullable=False)
    follow_up_type = db.Column(db.String(32))
    target_case_id = db.Column(db.Integer, db.ForeignKey("recycling_cases.id"))
    confidence = db.Column(db.Float)
    needs_clarification = db.Column(db.Boolean, nullable=False, default=False)
    decision_json = db.Column(db.Text, nullable=False)
    engine_version = db.Column(db.String(64), nullable=False)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
