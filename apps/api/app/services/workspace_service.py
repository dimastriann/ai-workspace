"""
AI Workspace API — Workspace Service

Handles creation and management of workspaces.
"""

import uuid
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database import Workspace, Document
from app.models.workspace import WorkspaceCreate


class WorkspaceService:
    @staticmethod
    async def create_workspace(data: WorkspaceCreate, db: AsyncSession) -> Workspace:
        """Create a new workspace entry."""
        db_workspace = Workspace(
            name=data.name,
            description=data.description
        )
        db.add(db_workspace)
        await db.commit()
        await db.refresh(db_workspace)
        return db_workspace

    @staticmethod
    async def list_workspaces(db: AsyncSession) -> List[Workspace]:
        """List all available workspaces."""
        result = await db.execute(select(Workspace).order_by(Workspace.created_at.desc()))
        return list(result.scalars().all())

    @staticmethod
    async def get_workspace(workspace_id: uuid.UUID, db: AsyncSession) -> Workspace | None:
        """Get a specific workspace by ID."""
        result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
        return result.scalar_one_or_none()


workspace_service = WorkspaceService()
