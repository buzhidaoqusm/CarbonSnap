"""add project cover_image_url

Revision ID: c2e8f1a3b7d5
Revises: b1f7d8c2a9e4
Create Date: 2026-04-07 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "c2e8f1a3b7d5"
down_revision = "b1f7d8c2a9e4"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "projects" in existing_tables:
        existing_columns = {col["name"] for col in inspector.get_columns("projects")}
        if "cover_image_url" not in existing_columns:
            with op.batch_alter_table("projects", schema=None) as batch_op:
                batch_op.add_column(
                    sa.Column("cover_image_url", sa.String(length=512), nullable=True)
                )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "projects" in existing_tables:
        existing_columns = {col["name"] for col in inspector.get_columns("projects")}
        if "cover_image_url" in existing_columns:
            with op.batch_alter_table("projects", schema=None) as batch_op:
                batch_op.drop_column("cover_image_url")
