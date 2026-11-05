"""Add durable ticket scheduling and isolate LangGraph checkpoint tables."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tickets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("customer_id", sa.String(40), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("initial_input", JSONB(), nullable=False),
        sa.Column("input", JSONB(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column(
            "available_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("outcome", JSONB(), nullable=True),
        sa.Column("decision", JSONB(), nullable=True),
        sa.Column("history", JSONB(), nullable=False),
        sa.UniqueConstraint("customer_id", "request_id", name="uq_ticket_customer_request"),
    )
    op.create_index("ix_tickets_status", "tickets", ["status"])
    op.create_table(
        "completion_events",
        sa.Column("ticket_id", sa.Uuid(), sa.ForeignKey("tickets.id"), primary_key=True),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.execute("CREATE SCHEMA IF NOT EXISTS supportops_graph")


def downgrade() -> None:
    op.drop_table("completion_events")
    op.drop_index("ix_tickets_status", table_name="tickets")
    op.drop_table("tickets")
    # Keep checkpoint history available to operators during rollback.
