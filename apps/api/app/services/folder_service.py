"""Business logic for workspace document folders."""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import (
    DocumentNotFoundError,
    FolderConflictError,
    FolderNotFoundError,
    WorkspaceNotFoundError,
)
from app.models.database import Document, DocumentFolder, Workspace
from app.models.folder import FolderCreate, FolderTree, FolderUpdate


def _normalize_name(name: str) -> str:
    return " ".join(name.split())


class FolderService:
    async def list_folders(
        self, workspace_id: uuid.UUID, db: AsyncSession
    ) -> list[FolderTree]:
        """Return the workspace folder tree."""
        if await db.get(Workspace, workspace_id) is None:
            raise WorkspaceNotFoundError("Workspace not found")

        result = await db.execute(
            select(DocumentFolder)
            .where(DocumentFolder.workspace_id == workspace_id)
            .order_by(DocumentFolder.name)
        )
        folders = list(result.scalars().all())

        nodes = {
            str(folder.id): FolderTree(
                id=str(folder.id),
                workspace_id=str(folder.workspace_id),
                parent_id=str(folder.parent_id) if folder.parent_id else None,
                name=folder.name,
                created_at=folder.created_at,
                updated_at=folder.updated_at,
            )
            for folder in folders
        }

        roots: list[FolderTree] = []
        for folder in folders:
            node = nodes[str(folder.id)]
            parent = nodes.get(str(folder.parent_id)) if folder.parent_id else None
            if parent is None:
                roots.append(node)
            else:
                parent.children.append(node)
        return roots

    async def create_folder(
        self, data: FolderCreate, db: AsyncSession
    ) -> DocumentFolder:
        """Create a folder after validating the workspace, parent, and name."""
        if await db.get(Workspace, data.workspace_id) is None:
            raise WorkspaceNotFoundError("Workspace not found")

        name = _normalize_name(data.name)
        if not name:
            raise FolderConflictError("Folder name is required")

        if data.parent_id is not None:
            parent = await db.get(DocumentFolder, data.parent_id)
            if parent is None or parent.workspace_id != data.workspace_id:
                raise FolderNotFoundError("Parent folder not found")

        await self._check_duplicate(data.workspace_id, data.parent_id, name, db)

        folder = DocumentFolder(
            workspace_id=data.workspace_id,
            parent_id=data.parent_id,
            name=name,
        )
        db.add(folder)
        await db.commit()
        await db.refresh(folder)
        return folder

    async def update_folder(
        self, folder_id: uuid.UUID, data: FolderUpdate, db: AsyncSession
    ) -> DocumentFolder:
        """Rename and/or move a folder."""
        folder = await self._get_folder(folder_id, db)
        fields = data.model_fields_set
        if not fields:
            raise FolderConflictError("No changes supplied")

        if "name" in fields and data.name is not None:
            name = _normalize_name(data.name)
            if not name:
                raise FolderConflictError("Folder name is required")
            await self._check_duplicate(
                folder.workspace_id, folder.parent_id, name, db, exclude_ids={folder.id}
            )
            folder.name = name

        if "parent_id" in fields:
            parent_id = data.parent_id
            if parent_id is not None:
                parent = await db.get(DocumentFolder, parent_id)
                if parent is None or parent.workspace_id != folder.workspace_id:
                    raise FolderNotFoundError("Parent folder not found")
                if await self._is_descendant(parent_id, folder.id, db):
                    raise FolderConflictError(
                        "Cannot move a folder into its descendant"
                    )
            await self._check_duplicate(
                folder.workspace_id, parent_id, folder.name, db, exclude_ids={folder.id}
            )
            folder.parent_id = parent_id

        await db.commit()
        await db.refresh(folder)
        return folder

    async def delete_folder(
        self, folder_id: uuid.UUID, strategy: str, db: AsyncSession
    ) -> DocumentFolder:
        """Delete a folder, optionally moving its contents to the parent."""
        folder = await self._get_folder(folder_id, db)

        children = list(
            (
                await db.execute(
                    select(DocumentFolder).where(DocumentFolder.parent_id == folder.id)
                )
            )
            .scalars()
            .all()
        )
        document_count = (
            await db.execute(
                select(func.count())
                .select_from(Document)
                .where(Document.folder_id == folder.id)
            )
        ).scalar_one()

        if (children or document_count) and strategy != "move_parent":
            raise FolderConflictError(
                "Folder is not empty; move contents to the parent or delete them first"
            )

        if strategy == "move_parent":
            for child in children:
                await self._check_duplicate(
                    folder.workspace_id,
                    folder.parent_id,
                    child.name,
                    db,
                    exclude_ids={child.id, folder.id},
                )
                child.parent_id = folder.parent_id

            await db.execute(
                update(Document)
                .where(Document.folder_id == folder.id)
                .values(folder_id=folder.parent_id)
            )
        elif children or document_count:
            raise FolderConflictError("Folder is not empty")

        await db.delete(folder)
        await db.commit()
        return folder

    async def move_document(
        self, document_id: uuid.UUID, folder_id: uuid.UUID | None, db: AsyncSession
    ) -> Document:
        """Move a document into a folder in the same workspace."""
        document = await db.get(Document, document_id)
        if document is None:
            raise DocumentNotFoundError("Document not found")

        if folder_id is not None:
            folder = await db.get(DocumentFolder, folder_id)
            if folder is None or folder.workspace_id != document.workspace_id:
                raise FolderNotFoundError("Folder not found")

        document.folder_id = folder_id
        await db.commit()
        await db.refresh(document)
        return document

    async def _get_folder(
        self, folder_id: uuid.UUID, db: AsyncSession
    ) -> DocumentFolder:
        folder = await db.get(DocumentFolder, folder_id)
        if folder is None:
            raise FolderNotFoundError("Folder not found")
        return folder

    async def _check_duplicate(
        self,
        workspace_id: uuid.UUID,
        parent_id: uuid.UUID | None,
        name: str,
        db: AsyncSession,
        *,
        exclude_ids: set[uuid.UUID] | None = None,
    ) -> None:
        statement = select(DocumentFolder.id).where(
            DocumentFolder.workspace_id == workspace_id,
            DocumentFolder.parent_id == parent_id,
            func.lower(DocumentFolder.name) == name.lower(),
        )
        if exclude_ids:
            statement = statement.where(DocumentFolder.id.not_in(exclude_ids))
        if (await db.execute(statement)).first() is not None:
            raise FolderConflictError("A folder with this name already exists here")

    async def _is_descendant(
        self,
        candidate_id: uuid.UUID,
        folder_id: uuid.UUID,
        db: AsyncSession,
    ) -> bool:
        current_id: uuid.UUID | None = candidate_id
        seen: set[uuid.UUID] = set()
        while current_id is not None:
            if current_id == folder_id:
                return True
            if current_id in seen:
                return False
            seen.add(current_id)
            current = await db.get(DocumentFolder, current_id)
            if current is None:
                return False
            current_id = current.parent_id
        return False


folder_service = FolderService()
