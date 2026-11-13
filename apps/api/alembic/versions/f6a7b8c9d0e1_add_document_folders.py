"""add document folders

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-11-13

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create document_folders and link documents to folders."""
    op.create_table(
        "document_folders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["parent_id"], ["document_folders.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "parent_id",
            "name",
            name="uq_document_folders_scope_name",
        ),
    )
    op.create_index(
        op.f("ix_document_folders_workspace_id"),
        "document_folders",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_folders_parent_id"),
        "document_folders",
        ["parent_id"],
        unique=False,
    )

    op.add_column("documents", sa.Column("folder_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_documents_folder_id_document_folders",
        "documents",
        "document_folders",
        ["folder_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_documents_folder_id"),
        "documents",
        ["folder_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove document folder links."""
    op.drop_index(op.f("ix_documents_folder_id"), table_name="documents")
    op.drop_constraint(
        "fk_documents_folder_id_document_folders",
        "documents",
        type_="foreignkey",
    )
    op.drop_column("documents", "folder_id")

    op.drop_index(op.f("ix_document_folders_parent_id"), table_name="document_folders")
    op.drop_index(
        op.f("ix_document_folders_workspace_id"), table_name="document_folders"
    )
    op.drop_table("document_folders")
