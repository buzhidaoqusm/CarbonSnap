"""add ai chat tables

Revision ID: 8d4b84b83f0a
Revises: 3361539ba606
Create Date: 2026-03-23 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8d4b84b83f0a"
down_revision = "3361539ba606"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_conversations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_pending_action", sa.String(length=32), nullable=False),
        sa.Column("session_context_json", sa.Text(), nullable=True),
        sa.Column("last_message_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ai_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("message_type", sa.String(length=32), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("content_json", sa.Text(), nullable=True),
        sa.Column("related_analysis_id", sa.Integer(), nullable=True),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["ai_conversations.id"]),
        sa.ForeignKeyConstraint(
            ["related_analysis_id"], ["waste_analysis_records.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "conversation_id",
            "sequence_no",
            name="uq_ai_messages_conversation_sequence",
        ),
    )


def downgrade():
    op.drop_table("ai_messages")
    op.drop_table("ai_conversations")
