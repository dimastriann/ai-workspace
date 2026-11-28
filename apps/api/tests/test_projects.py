"""Tests for chat project CRUD."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import ChatSession, Document, Workspace


async def _make_workspace(db: AsyncSession) -> Workspace:
    workspace = Workspace(id=uuid.uuid4(), name="WS")
    db.add(workspace)
    await db.commit()
    return workspace


@pytest.mark.asyncio
async def test_project_crud(
    member_client: AsyncClient, db_session: AsyncSession
) -> None:
    workspace = await _make_workspace(db_session)

    created = await member_client.post(
        "/api/projects",
        json={
            "workspace_id": str(workspace.id),
            "name": "Research",
            "description": "Papers",
            "instructions": "Cite sources.",
            "memory_mode": "project",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["name"] == "Research"
    assert body["memory_mode"] == "project"
    assert body["instructions"] == "Cite sources."

    listed = await member_client.get(f"/api/projects?workspace_id={workspace.id}")
    assert listed.status_code == 200
    assert [item["name"] for item in listed.json()] == ["Research"]

    duplicate = await member_client.post(
        "/api/projects",
        json={"workspace_id": str(workspace.id), "name": "Research"},
    )
    assert duplicate.status_code == 400

    updated = await member_client.patch(
        f"/api/projects/{body['id']}",
        json={"memory_mode": "workspace", "instructions": ""},
    )
    assert updated.status_code == 200
    assert updated.json()["memory_mode"] == "workspace"

    # Deleting the project keeps sessions and documents in the workspace.
    session = ChatSession(id=uuid.uuid4(), workspace_id=workspace.id, user_id=None)
    session.project_id = uuid.UUID(body["id"])
    document = Document(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        filename="doc.md",
        document_type="markdown",
        size_bytes=3,
    )
    document.project_id = uuid.UUID(body["id"])
    db_session.add(session)
    db_session.add(document)
    await db_session.commit()

    deleted = await member_client.delete(f"/api/projects/{body['id']}")
    assert deleted.status_code == 204

    await db_session.refresh(session)
    await db_session.refresh(document)
    assert session.project_id is None
    assert document.project_id is None
