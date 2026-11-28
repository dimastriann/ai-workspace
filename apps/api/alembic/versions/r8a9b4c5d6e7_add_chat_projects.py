"""add chat projects

Revision ID: r8a9b4c5d6e7
Revises: q7f8a9b4c5d6
Create Date: 2026-11-24

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "r8a9b4c5d6e7"
down_revision: str | Sequence[str] | None = "q7f8a9b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Projects group chat sessions with instructions and memory scope."""
    op.create_table(
        "chat_projects",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("memory_mode", sa.String(20), nullable=False, server_default="workspace"),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("workspace_id", "name", name="uq_chat_projects_scope_name"),
    )
    op.create_index(
        op.f("ix_chat_projects_workspace_id"), "chat_projects", ["workspace_id"]
    )
    op.add_column(
        "chat_sessions",
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("chat_projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        op.f("ix_chat_sessions_project_id"), "chat_sessions", ["project_id"]
    )
    op.add_column(
        "documents",
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("chat_projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(op.f("ix_documents_project_id"), "documents", ["project_id"])


def downgrade() -> None:
    """Remove project grouping."""
    op.drop_index(op.f("ix_documents_project_id"), table_name="documents")
    op.drop_column("documents", "project_id")
    op.drop_index(op.f("ix_chat_sessions_project_id"), table_name="chat_sessions")
    op.drop_column("chat_sessions", "project_id")
    op.drop_index(op.f("ix_chat_projects_workspace_id"), table_name="chat_projects")
    op.drop_table("chat_projects")
