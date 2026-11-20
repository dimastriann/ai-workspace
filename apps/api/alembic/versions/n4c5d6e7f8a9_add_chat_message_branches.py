"""add chat message branches

Revision ID: n4c5d6e7f8a9
Revises: m3b4c5d6e7f8
Create Date: 2026-11-18

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "n4c5d6e7f8a9"
down_revision: str | Sequence[str] | None = "m3b4c5d6e7f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Link messages into a conversation tree and select the active branch."""
    op.add_column("chat_messages", sa.Column("parent_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_chat_messages_parent_id_chat_messages",
        "chat_messages",
        "chat_messages",
        ["parent_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_chat_messages_parent_id"),
        "chat_messages",
        ["parent_id"],
        unique=False,
    )
    op.add_column(
        "chat_sessions", sa.Column("active_leaf_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        "fk_chat_sessions_active_leaf_id_chat_messages",
        "chat_sessions",
        "chat_messages",
        ["active_leaf_id"],
        ["id"],
        ondelete="SET NULL",
    )

    connection = op.get_bind()
    session_rows = connection.execute(sa.text("SELECT id FROM chat_sessions"))
    if session_rows is None:
        return
    sessions = session_rows.fetchall()
    for (session_id,) in sessions:
        messages = connection.execute(
            sa.text(
                "SELECT id FROM chat_messages WHERE session_id = :session_id "
                "ORDER BY created_at, id"
            ),
            {"session_id": session_id},
        ).fetchall()
        previous: uuid.UUID | None = None
        for (message_id,) in messages:
            connection.execute(
                sa.text(
                    "UPDATE chat_messages SET parent_id = :parent_id WHERE id = :id"
                ),
                {"parent_id": previous, "id": message_id},
            )
            previous = message_id
        if previous is not None:
            connection.execute(
                sa.text(
                    "UPDATE chat_sessions SET active_leaf_id = :leaf_id "
                    "WHERE id = :session_id"
                ),
                {"leaf_id": previous, "session_id": session_id},
            )


def downgrade() -> None:
    """Remove conversation branching."""
    op.drop_constraint(
        "fk_chat_sessions_active_leaf_id_chat_messages",
        "chat_sessions",
        type_="foreignkey",
    )
    op.drop_column("chat_sessions", "active_leaf_id")
    op.drop_index(op.f("ix_chat_messages_parent_id"), table_name="chat_messages")
    op.drop_constraint(
        "fk_chat_messages_parent_id_chat_messages", "chat_messages", type_="foreignkey"
    )
    op.drop_column("chat_messages", "parent_id")
