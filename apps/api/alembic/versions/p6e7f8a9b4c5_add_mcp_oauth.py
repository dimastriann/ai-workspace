"""add mcp oauth tokens

Revision ID: p6e7f8a9b4c5
Revises: o5d6e7f8a9b4
Create Date: 2026-11-23

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "p6e7f8a9b4c5"
down_revision: str | Sequence[str] | None = "o5d6e7f8a9b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Store the encrypted OAuth token bundle for remote MCP servers."""
    op.add_column("mcp_servers", sa.Column("oauth_encrypted", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove OAuth token storage."""
    op.drop_column("mcp_servers", "oauth_encrypted")
