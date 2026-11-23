"""add chat attachment images

Revision ID: q7f8a9b4c5d6
Revises: p6e7f8a9b4c5
Create Date: 2026-11-24

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "q7f8a9b4c5d6"
down_revision: str | Sequence[str] | None = "p6e7f8a9b4c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Mark image attachments so they are served and sent as images."""
    op.add_column(
        "chat_attachments",
        sa.Column("is_image", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    """Remove the image flag."""
    op.drop_column("chat_attachments", "is_image")
