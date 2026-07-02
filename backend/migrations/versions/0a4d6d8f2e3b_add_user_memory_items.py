"""add user memory items

Revision ID: 0a4d6d8f2e3b
Revises: d71c6e1f9a21
Create Date: 2026-03-24 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "0a4d6d8f2e3b"
down_revision = "d71c6e1f9a21"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_memory_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("memory_type", sa.String(length=32), nullable=False),
        sa.Column("memory_key", sa.String(length=128), nullable=False),
        sa.Column("value_json", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_message_id", sa.Integer(), nullable=True),
        sa.Column("conversation_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["ai_conversations.id"]),
        sa.ForeignKeyConstraint(["source_message_id"], ["ai_messages.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_user_memory_items_user_status_type_key",
        "user_memory_items",
        ["user_id", "status", "memory_type", "memory_key"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_user_memory_items_user_status_type_key", table_name="user_memory_items")
    op.drop_table("user_memory_items")
