"""add document conversions

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-11-13

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: str | Sequence[str] | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the document_conversions table."""
    op.create_table(
        "document_conversions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "include_images", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("markdown_path", sa.String(length=500), nullable=True),
        sa.Column("assets_path", sa.String(length=500), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_document_conversions_document_id"),
        "document_conversions",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_conversions_status"),
        "document_conversions",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the document_conversions table."""
    op.drop_index(
        op.f("ix_document_conversions_status"),
        table_name="document_conversions",
    )
    op.drop_index(
        op.f("ix_document_conversions_document_id"),
        table_name="document_conversions",
    )
    op.drop_table("document_conversions")
