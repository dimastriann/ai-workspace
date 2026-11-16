"""Business logic for saved agent workflows."""

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import (
    WorkflowNotFoundError,
    WorkflowValidationError,
    WorkspaceNotFoundError,
)
from app.models.database import User, Workflow, WorkflowStep, Workspace
from app.models.workflow import (
    WorkflowCreate,
    WorkflowStepInput,
    WorkflowUpdate,
)
from app.services.skills import skill_registry


class WorkflowService:
    async def create_workflow(
        self, data: WorkflowCreate, user: User, db: AsyncSession
    ) -> Workflow:
        """Validate and persist a new workflow."""
        if await db.get(Workspace, data.workspace_id) is None:
            raise WorkspaceNotFoundError("Workspace not found")

        name = self._normalize_name(data.name)
        await self._validate_steps(data.steps)
        await self._check_duplicate_name(data.workspace_id, user.id, name, db)

        workflow = Workflow(
            workspace_id=data.workspace_id,
            user_id=user.id,
            name=name,
            description=data.description.strip(),
            steps=[
                WorkflowStep(
                    ordinal=index,
                    instruction=step.instruction.strip(),
                    skill=step.skill,
                )
                for index, step in enumerate(data.steps)
            ],
        )
        db.add(workflow)
        await db.commit()
        return await self._get_workflow(workflow.id, user, db)

    async def list_workflows(
        self, workspace_id: uuid.UUID, user: User, db: AsyncSession
    ) -> list[Workflow]:
        """List a user's workflows in a workspace."""
        if await db.get(Workspace, workspace_id) is None:
            raise WorkspaceNotFoundError("Workspace not found")
        result = await db.execute(
            select(Workflow)
            .options(selectinload(Workflow.steps))
            .where(
                Workflow.workspace_id == workspace_id,
                Workflow.user_id == user.id,
            )
            .order_by(Workflow.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_workflow(
        self, workflow_id: uuid.UUID, user: User, db: AsyncSession
    ) -> Workflow:
        """Load one workflow with steps."""
        return await self._get_workflow(workflow_id, user, db)

    async def update_workflow(
        self, workflow_id: uuid.UUID, data: WorkflowUpdate, user: User, db: AsyncSession
    ) -> Workflow:
        """Update workflow metadata and optionally replace steps."""
        workflow = await self._get_workflow(workflow_id, user, db)
        fields = data.model_fields_set
        if not fields:
            raise WorkflowValidationError("No changes supplied")

        if "name" in fields and data.name is not None:
            name = self._normalize_name(data.name)
            await self._check_duplicate_name(
                workflow.workspace_id,
                user.id,
                name,
                db,
                exclude_id=workflow.id,
            )
            workflow.name = name

        if "description" in fields and data.description is not None:
            workflow.description = data.description.strip()

        if "steps" in fields and data.steps is not None:
            await self._validate_steps(data.steps)
            await db.execute(
                delete(WorkflowStep).where(WorkflowStep.workflow_id == workflow.id)
            )
            await db.flush()
            for index, step in enumerate(data.steps):
                db.add(
                    WorkflowStep(
                        workflow_id=workflow.id,
                        ordinal=index,
                        instruction=step.instruction.strip(),
                        skill=step.skill,
                    )
                )

        await db.commit()
        return await self._get_workflow(workflow.id, user, db)

    async def delete_workflow(
        self, workflow_id: uuid.UUID, user: User, db: AsyncSession
    ) -> Workflow:
        """Delete a workflow and its steps."""
        workflow = await self._get_workflow(workflow_id, user, db)
        await db.delete(workflow)
        await db.commit()
        return workflow

    async def _get_workflow(
        self, workflow_id: uuid.UUID, user: User, db: AsyncSession
    ) -> Workflow:
        result = await db.execute(
            select(Workflow)
            .options(selectinload(Workflow.steps))
            .where(Workflow.id == workflow_id)
            .execution_options(populate_existing=True)
        )
        workflow = result.scalar_one_or_none()
        if workflow is None or workflow.user_id != user.id:
            raise WorkflowNotFoundError("Workflow not found")
        return workflow

    async def _validate_steps(self, steps: list[WorkflowStepInput]) -> None:
        if not steps:
            raise WorkflowValidationError("A workflow needs at least one step")
        for step in steps:
            if not step.instruction.strip():
                raise WorkflowValidationError("Step instruction is required")
            if step.skill and skill_registry.get(step.skill) is None:
                raise WorkflowValidationError(f"Unknown skill: {step.skill}")

    async def _check_duplicate_name(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        name: str,
        db: AsyncSession,
        *,
        exclude_id: uuid.UUID | None = None,
    ) -> None:
        statement = select(Workflow.id).where(
            Workflow.workspace_id == workspace_id,
            Workflow.user_id == user_id,
            func.lower(Workflow.name) == name.lower(),
        )
        if exclude_id is not None:
            statement = statement.where(Workflow.id != exclude_id)
        if (await db.execute(statement)).first() is not None:
            raise WorkflowValidationError("A workflow with this name already exists")

    @staticmethod
    def _normalize_name(name: str) -> str:
        normalized = " ".join(name.split())
        if not normalized:
            raise WorkflowValidationError("Workflow name is required")
        return normalized


workflow_service = WorkflowService()
