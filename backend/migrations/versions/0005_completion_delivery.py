"""Record acknowledgements from the n8n demo notification channel."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("completion_events", sa.Column("delivered_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("completion_events", "delivered_at")
