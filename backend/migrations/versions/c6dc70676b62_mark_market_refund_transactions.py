"""mark market refund transactions

cancel_order used to refund the buyer with a 'market_order' earn transaction,
the same shape as the seller's settlement, so refunds counted as earned points.
Refunds are now written as 'market_refund'; this moves the old ones over. The
buyer of an order is only ever credited for it by a refund (nobody can buy
their own item), so a 'market_order' earn row for the order's buyer is one.

Revision ID: c6dc70676b62
Revises: c2e8f1a3b7d5
Create Date: 2026-10-02 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "c6dc70676b62"
down_revision = "c2e8f1a3b7d5"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        sa.text(
            "UPDATE transactions SET source_type = 'market_refund' "
            "WHERE type = 'earn' AND source_type = 'market_order' "
            "AND EXISTS (SELECT 1 FROM orders "
            "WHERE orders.id = transactions.source_id "
            "AND orders.buyer_id = transactions.user_id)"
        )
    )


def downgrade():
    # 'market_refund' did not exist before this revision.
    op.execute(
        sa.text(
            "UPDATE transactions SET source_type = 'market_order' "
            "WHERE source_type = 'market_refund'"
        )
    )
