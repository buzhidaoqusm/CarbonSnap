"""add recommendation profile tables

Revision ID: b1f7d8c2a9e4
Revises: 4c1a9a7b6f2d
Create Date: 2026-03-27 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "b1f7d8c2a9e4"
down_revision = "4c1a9a7b6f2d"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "user_behavior_events" in existing_tables:
        existing_columns = {column["name"] for column in inspector.get_columns("user_behavior_events")}
        with op.batch_alter_table("user_behavior_events", schema=None) as batch_op:
            if "target_type" not in existing_columns:
                batch_op.add_column(sa.Column("target_type", sa.String(length=32), nullable=True))
            if "topic_payload_json" not in existing_columns:
                batch_op.add_column(sa.Column("topic_payload_json", sa.Text(), nullable=True))
            if "context_json" not in existing_columns:
                batch_op.add_column(sa.Column("context_json", sa.Text(), nullable=True))

    if "content_topic_assignments" not in existing_tables:
        op.create_table(
            "content_topic_assignments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("domain", sa.String(length=32), nullable=False),
            sa.Column("content_type", sa.String(length=32), nullable=False),
            sa.Column("content_id", sa.Integer(), nullable=False),
            sa.Column("topic_id", sa.String(length=64), nullable=False),
            sa.Column("confidence_score", sa.Float(), nullable=False),
            sa.Column("source", sa.String(length=32), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "domain",
                "content_type",
                "content_id",
                "topic_id",
                name="uq_content_topic_assignments_content_topic",
            ),
        )

    if "user_preference_profiles" not in existing_tables:
        op.create_table(
            "user_preference_profiles",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("profile_type", sa.String(length=32), nullable=False),
            sa.Column("profile_key", sa.String(length=128), nullable=False),
            sa.Column("raw_score", sa.Float(), nullable=False),
            sa.Column("normalized_score", sa.Float(), nullable=False),
            sa.Column("confidence_score", sa.Float(), nullable=False),
            sa.Column("event_count", sa.Integer(), nullable=False),
            sa.Column("source_domains_json", sa.Text(), nullable=False),
            sa.Column("last_event_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "user_id",
                "profile_type",
                "profile_key",
                name="uq_user_preference_profiles_user_profile_key",
            ),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "user_preference_profiles" in existing_tables:
        op.drop_table("user_preference_profiles")

    if "content_topic_assignments" in existing_tables:
        op.drop_table("content_topic_assignments")

    if "user_behavior_events" in existing_tables:
        existing_columns = {column["name"] for column in inspector.get_columns("user_behavior_events")}
        columns_to_drop = [
            column_name
            for column_name in ("context_json", "topic_payload_json", "target_type")
            if column_name in existing_columns
        ]
        if columns_to_drop:
            with op.batch_alter_table("user_behavior_events", schema=None) as batch_op:
                for column_name in columns_to_drop:
                    batch_op.drop_column(column_name)
