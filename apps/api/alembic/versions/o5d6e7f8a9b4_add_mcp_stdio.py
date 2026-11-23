"""add mcp stdio transport

Revision ID: o5d6e7f8a9b4
Revises: n4c5d6e7f8a9
Create Date: 2026-11-23

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "o5d6e7f8a9b4"
down_revision: str | Sequence[str] | None = "n4c5d6e7f8a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store the stdio command argv and encrypted environment variables."""
    op.add_column("mcp_servers", sa.Column("command", sa.Text(), nullable=True))
    op.add_column("mcp_servers", sa.Column("env_encrypted", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove stdio command storage."""
    op.drop_column("mcp_servers", "env_encrypted")
    op.drop_column("mcp_servers", "command")
