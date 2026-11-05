"""Add shop orders, customers and the action ledger."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("customers", sa.Column("id", sa.String(40), primary_key=True))
    op.create_table(
        "orders",
        sa.Column("id", sa.String(40), primary_key=True),
        sa.Column("customer_id", sa.String(40), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("items", JSONB(), nullable=False),
        sa.Column("tracking_ids", JSONB(), nullable=False),
        sa.Column("payment_sources", JSONB(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
    op.create_table(
        "order_actions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("order_id", sa.String(40), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("request", JSONB(), nullable=False),
        sa.Column("result", JSONB(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("order_actions")
    op.drop_index("ix_orders_customer_id", table_name="orders")
    op.drop_table("orders")
    op.drop_table("customers")
