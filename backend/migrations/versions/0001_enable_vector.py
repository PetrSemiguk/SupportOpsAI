"""Enable the vector extension for policy retrieval."""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    # The database may share this extension with other applications.
    # Retain it when rolling back this application's schema.
    pass
