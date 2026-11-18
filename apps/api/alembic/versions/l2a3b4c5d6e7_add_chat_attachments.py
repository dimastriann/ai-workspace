"""add chat attachments

Revision ID: l2a3b4c5d6e7
Revises: k1f2a3b4c5d6
Create Date: 2026-11-17

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "l2a3b4c5d6e7"
down_revision: str | Sequence[str] | None = "k1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create chat attachments and link message attachments."""
    op.create_table(
        "chat_attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_chat_attachments_user_id"),
        "chat_attachments",
        ["user_id"],
        unique=False,
    )
    op.add_column(
        "chat_messages",
        sa.Column(
            "attachment_ids",
            sa.Text(),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    """Remove chat attachments."""
    op.drop_column("chat_messages", "attachment_ids")
    op.drop_index(op.f("ix_chat_attachments_user_id"), table_name="chat_attachments")
    op.drop_table("chat_attachments")
