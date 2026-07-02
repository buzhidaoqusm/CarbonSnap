"""add ai message decisions

Revision ID: 3b5c1e2d9f4a
Revises: 0a4d6d8f2e3b
Create Date: 2026-03-24 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "3b5c1e2d9f4a"
down_revision = "0a4d6d8f2e3b"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "ai_message_decisions" not in existing_tables:
        op.create_table(
            "ai_message_decisions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("conversation_id", sa.Integer(), nullable=False),
            sa.Column("user_message_id", sa.Integer(), nullable=False),
            sa.Column("intent", sa.String(length=32), nullable=False),
            sa.Column("follow_up_type", sa.String(length=32), nullable=True),
            sa.Column("target_case_id", sa.Integer(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column(
                "needs_clarification",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column("decision_json", sa.Text(), nullable=False),
            sa.Column("engine_version", sa.String(length=64), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["conversation_id"], ["ai_conversations.id"]),
            sa.ForeignKeyConstraint(["target_case_id"], ["recycling_cases.id"]),
            sa.ForeignKeyConstraint(["user_message_id"], ["ai_messages.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    existing_indexes = {index["name"] for index in inspector.get_indexes("ai_message_decisions")}
    if "ix_ai_message_decisions_conversation_id" not in existing_indexes:
        op.create_index(
            "ix_ai_message_decisions_conversation_id",
            "ai_message_decisions",
            ["conversation_id"],
            unique=False,
        )
    if "ix_ai_message_decisions_user_message_id" not in existing_indexes:
        op.create_index(
            "ix_ai_message_decisions_user_message_id",
            "ai_message_decisions",
            ["user_message_id"],
            unique=False,
        )


def downgrade():
    op.drop_index("ix_ai_message_decisions_user_message_id", table_name="ai_message_decisions")
    op.drop_index("ix_ai_message_decisions_conversation_id", table_name="ai_message_decisions")
    op.drop_table("ai_message_decisions")
