"""add recycling case and audit tables

Revision ID: d71c6e1f9a21
Revises: 8d4b84b83f0a
Create Date: 2026-03-23 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d71c6e1f9a21"
down_revision = "8d4b84b83f0a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "recycling_cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("origin_message_id", sa.Integer(), nullable=False),
        sa.Column("waste_type_predicted", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("estimated_weight_kg", sa.Float(), nullable=False),
        sa.Column("expected_co2_saved_kg", sa.Float(), nullable=False),
        sa.Column("expected_carbon_points", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("latest_audit_attempt_no", sa.Integer(), nullable=False),
        sa.Column("approved_analysis_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["ai_conversations.id"]),
        sa.ForeignKeyConstraint(["origin_message_id"], ["ai_messages.id"]),
        sa.ForeignKeyConstraint(
            ["approved_analysis_id"], ["waste_analysis_records.id"]
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "recycling_audit_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recycling_case_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("audit_image_url", sa.String(length=256), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("audit_result", sa.String(length=16), nullable=False),
        sa.Column("auditor_confidence", sa.Float(), nullable=False),
        sa.Column("audit_reason", sa.Text(), nullable=True),
        sa.Column("audit_response_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["ai_conversations.id"]),
        sa.ForeignKeyConstraint(["recycling_case_id"], ["recycling_cases.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "recycling_case_id",
            "attempt_no",
            name="uq_recycling_audit_attempt_case_attempt",
        ),
    )

    with op.batch_alter_table("waste_analysis_records", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("conversation_id", sa.Integer(), nullable=True),
        )
        batch_op.add_column(
            sa.Column("recycling_case_id", sa.Integer(), nullable=True),
        )
        batch_op.add_column(
            sa.Column("approved_audit_attempt_id", sa.Integer(), nullable=True),
        )
        batch_op.add_column(
            sa.Column(
                "confidence",
                sa.Float(),
                nullable=False,
                server_default=sa.text("0.0"),
            ),
        )
        batch_op.add_column(
            sa.Column(
                "estimated_weight_kg",
                sa.Float(),
                nullable=False,
                server_default=sa.text("0.0"),
            ),
        )
        batch_op.create_foreign_key(
            "fk_waste_analysis_records_conversation_id_ai_conversations",
            "ai_conversations",
            ["conversation_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_waste_analysis_records_recycling_case_id_recycling_cases",
            "recycling_cases",
            ["recycling_case_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_waste_analysis_records_approved_audit_attempt_id_recycling_audit_attempts",
            "recycling_audit_attempts",
            ["approved_audit_attempt_id"],
            ["id"],
        )


def downgrade():
    with op.batch_alter_table("waste_analysis_records", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_waste_analysis_records_approved_audit_attempt_id_recycling_audit_attempts",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_waste_analysis_records_recycling_case_id_recycling_cases",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_waste_analysis_records_conversation_id_ai_conversations",
            type_="foreignkey",
        )
        batch_op.drop_column("estimated_weight_kg")
        batch_op.drop_column("confidence")
        batch_op.drop_column("approved_audit_attempt_id")
        batch_op.drop_column("recycling_case_id")
        batch_op.drop_column("conversation_id")
    op.drop_table("recycling_audit_attempts")
    op.drop_table("recycling_cases")
