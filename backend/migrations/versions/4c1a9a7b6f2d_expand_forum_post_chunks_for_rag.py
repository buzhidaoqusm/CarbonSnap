"""expand forum post chunks for rag

Revision ID: 4c1a9a7b6f2d
Revises: 3b5c1e2d9f4a
Create Date: 2026-03-26 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "4c1a9a7b6f2d"
down_revision = "3b5c1e2d9f4a"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {
        column["name"] for column in inspector.get_columns("forum_post_chunks")
    }

    if "chunk_index" not in existing_columns:
        op.add_column(
            "forum_post_chunks",
            sa.Column(
                "chunk_index",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )
        existing_columns.add("chunk_index")

    if "section_title" not in existing_columns:
        op.add_column(
            "forum_post_chunks",
            sa.Column("section_title", sa.String(length=256), nullable=True),
        )
        existing_columns.add("section_title")

    if "chunk_version" not in existing_columns:
        op.add_column(
            "forum_post_chunks",
            sa.Column(
                "chunk_version",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("1"),
            ),
        )
        existing_columns.add("chunk_version")

    if bind.dialect.name != "sqlite":
        if "chunk_index" in existing_columns:
            op.alter_column("forum_post_chunks", "chunk_index", server_default=None)
        if "chunk_version" in existing_columns:
            op.alter_column("forum_post_chunks", "chunk_version", server_default=None)


def downgrade():
    with op.batch_alter_table("forum_post_chunks", schema=None) as batch_op:
        batch_op.drop_column("chunk_version")
        batch_op.drop_column("section_title")
        batch_op.drop_column("chunk_index")
