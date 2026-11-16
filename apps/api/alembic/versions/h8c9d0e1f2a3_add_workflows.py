"""add workflows

Revision ID: h8c9d0e1f2a3
Revises: g7b8c9d0e1f2
Create Date: 2026-11-13

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "h8c9d0e1f2a3"
down_revision: str | Sequence[str] | None = "g7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create workflows and link agent runs to them."""
    op.create_table(
        "workflows",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_workflows_workspace_id"), "workflows", ["workspace_id"], unique=False
    )
    op.create_index(
        op.f("ix_workflows_user_id"), "workflows", ["user_id"], unique=False
    )

    op.create_table(
        "workflow_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("skill", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workflow_id", "ordinal", name="uq_workflow_steps_ordinal"),
    )
    op.create_index(
        op.f("ix_workflow_steps_workflow_id"),
        "workflow_steps",
        ["workflow_id"],
        unique=False,
    )

    op.add_column("agent_runs", sa.Column("workflow_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_agent_runs_workflow_id_workflows",
        "agent_runs",
        "workflows",
        ["workflow_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_agent_runs_workflow_id"),
        "agent_runs",
        ["workflow_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove workflows and the agent run link."""
    op.drop_index(op.f("ix_agent_runs_workflow_id"), table_name="agent_runs")
    op.drop_constraint(
        "fk_agent_runs_workflow_id_workflows", "agent_runs", type_="foreignkey"
    )
    op.drop_column("agent_runs", "workflow_id")

    op.drop_index(op.f("ix_workflow_steps_workflow_id"), table_name="workflow_steps")
    op.drop_table("workflow_steps")
    op.drop_index(op.f("ix_workflows_user_id"), table_name="workflows")
    op.drop_index(op.f("ix_workflows_workspace_id"), table_name="workflows")
    op.drop_table("workflows")
