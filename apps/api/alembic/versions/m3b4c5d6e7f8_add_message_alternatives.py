"""add message alternatives

Revision ID: m3b4c5d6e7f8
Revises: l2a3b4c5d6e7
Create Date: 2026-11-17

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "m3b4c5d6e7f8"
down_revision: str | Sequence[str] | None = "l2a3b4c5d6e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store alternative assistant responses for branching."""
    op.add_column(
        "chat_messages",
        sa.Column("alternatives", sa.Text(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "chat_messages",
        sa.Column(
            "active_alternative",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    """Remove assistant response alternatives."""
    op.drop_column("chat_messages", "active_alternative")
    op.drop_column("chat_messages", "alternatives")
