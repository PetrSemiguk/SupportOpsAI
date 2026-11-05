"""Persist versioned policy excerpts and embeddings."""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import VECTOR

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "policy_sections",
        sa.Column("document", sa.String(200), primary_key=True),
        sa.Column("section_id", sa.String(80), primary_key=True),
        sa.Column("model_id", sa.String(100), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("revision", sa.String(64), nullable=False),
        sa.Column("embedding", VECTOR(256), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("policy_sections")
