"""Chat project business logic."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ProjectNotFoundError, ProjectValidationError
from app.models.database import ChatProject, ChatSession, Document, User, Workspace
from app.models.project import ProjectCreate, ProjectUpdate

MEMORY_MODES = {"workspace", "project"}


class ProjectService:
    async def list_projects(
        self, workspace_id: uuid.UUID, db: AsyncSession
    ) -> list[ChatProject]:
        result = await db.execute(
            select(ChatProject)
            .where(ChatProject.workspace_id == workspace_id)
            .order_by(ChatProject.created_at)
        )
        return list(result.scalars().all())

    async def get_project(self, project_id: uuid.UUID, db: AsyncSession) -> ChatProject:
        project = await db.get(ChatProject, project_id)
        if project is None:
            raise ProjectNotFoundError("Project not found")
        return project

    async def create_project(
        self, data: ProjectCreate, user: User | None, db: AsyncSession
    ) -> ChatProject:
        name = " ".join(data.name.split())
        if not name:
            raise ProjectValidationError("Project name is required")
        if data.memory_mode not in MEMORY_MODES:
            raise ProjectValidationError("Invalid memory mode")

        try:
            workspace_id = uuid.UUID(data.workspace_id)
        except ValueError as exc:
            raise ProjectValidationError("Invalid workspace id") from exc
        workspace = await db.get(Workspace, workspace_id)
        if workspace is None:
            raise ProjectValidationError("Workspace not found")

        if await self._name_exists(name, workspace_id, db):
            raise ProjectValidationError("A project with this name already exists")

        project = ChatProject(
            workspace_id=workspace_id,
            name=name,
            description=data.description.strip(),
            instructions=data.instructions.strip(),
            memory_mode=data.memory_mode,
            created_by=user.id if user else None,
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)
        return project

    async def update_project(
        self, project_id: uuid.UUID, data: ProjectUpdate, db: AsyncSession
    ) -> ChatProject:
        project = await self.get_project(project_id, db)
        fields = data.model_fields_set

        if "name" in fields and data.name is not None:
            name = " ".join(data.name.split())
            if not name:
                raise ProjectValidationError("Project name is required")
            if await self._name_exists(name, project.workspace_id, db, project.id):
                raise ProjectValidationError("A project with this name already exists")
            project.name = name
        if "description" in fields and data.description is not None:
            project.description = data.description.strip()
        if "instructions" in fields and data.instructions is not None:
            project.instructions = data.instructions.strip()
        if "memory_mode" in fields and data.memory_mode is not None:
            if data.memory_mode not in MEMORY_MODES:
                raise ProjectValidationError("Invalid memory mode")
            project.memory_mode = data.memory_mode

        await db.commit()
        await db.refresh(project)
        return project

    async def delete_project(
        self, project_id: uuid.UUID, db: AsyncSession
    ) -> ChatProject:
        project = await self.get_project(project_id, db)
        await db.delete(project)
        await db.commit()
        return project

    async def counts(
        self, project_ids: list[uuid.UUID], db: AsyncSession
    ) -> dict[uuid.UUID, tuple[int, int]]:
        """Session and document counts per project id."""
        if not project_ids:
            return {}
        session_rows = (
            await db.execute(
                select(ChatSession.project_id, func.count())
                .where(ChatSession.project_id.in_(project_ids))
                .group_by(ChatSession.project_id)
            )
        ).all()
        document_rows = (
            await db.execute(
                select(Document.project_id, func.count())
                .where(Document.project_id.in_(project_ids))
                .group_by(Document.project_id)
            )
        ).all()
        sessions = {row[0]: int(row[1]) for row in session_rows if row[0]}
        documents = {row[0]: int(row[1]) for row in document_rows if row[0]}
        return {
            project_id: (sessions.get(project_id, 0), documents.get(project_id, 0))
            for project_id in project_ids
        }

    @staticmethod
    async def _name_exists(
        name: str,
        workspace_id: uuid.UUID,
        db: AsyncSession,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        statement = select(ChatProject.id).where(
            ChatProject.workspace_id == workspace_id,
            ChatProject.name == name,
        )
        if exclude_id is not None:
            statement = statement.where(ChatProject.id != exclude_id)
        return (await db.execute(statement)).first() is not None


project_service = ProjectService()
