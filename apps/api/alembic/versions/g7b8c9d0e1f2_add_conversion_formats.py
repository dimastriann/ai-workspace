"""add conversion formats

Revision ID: g7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-11-13

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "g7b8c9d0e1f2"
down_revision: str | Sequence[str] | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add output format and JSON path to conversions."""
    op.add_column(
        "document_conversions",
        sa.Column(
            "format",
            sa.String(length=20),
            nullable=False,
            server_default="markdown",
        ),
    )
    op.add_column(
        "document_conversions",
        sa.Column("json_path", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    """Remove conversion format metadata."""
    op.drop_column("document_conversions", "json_path")
    op.drop_column("document_conversions", "format")
