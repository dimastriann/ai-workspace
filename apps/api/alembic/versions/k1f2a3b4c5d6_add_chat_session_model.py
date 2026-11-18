"""add chat session model

Revision ID: k1f2a3b4c5d6
Revises: j0e1f2a3b4c5
Create Date: 2026-11-17

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "k1f2a3b4c5d6"
down_revision: str | Sequence[str] | None = "j0e1f2a3b4c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store the selected model per chat session."""
    op.add_column(
        "chat_sessions", sa.Column("model", sa.String(length=120), nullable=True)
    )


def downgrade() -> None:
    """Remove the per-session model."""
    op.drop_column("chat_sessions", "model")
