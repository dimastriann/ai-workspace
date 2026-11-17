"""add chat session owner

Revision ID: j0e1f2a3b4c5
Revises: i9d0e1f2a3b4
Create Date: 2026-11-17

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "j0e1f2a3b4c5"
down_revision: str | Sequence[str] | None = "i9d0e1f2a3b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Link chat sessions to their owner."""
    op.add_column("chat_sessions", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_chat_sessions_user_id_users",
        "chat_sessions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_chat_sessions_user_id"), "chat_sessions", ["user_id"], unique=False
    )


def downgrade() -> None:
    """Remove the chat session owner link."""
    op.drop_index(op.f("ix_chat_sessions_user_id"), table_name="chat_sessions")
    op.drop_constraint(
        "fk_chat_sessions_user_id_users", "chat_sessions", type_="foreignkey"
    )
    op.drop_column("chat_sessions", "user_id")
