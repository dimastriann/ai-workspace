"""Tests for document folders and document moves."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Document, Workspace


async def _create_workspace(db_session: AsyncSession) -> uuid.UUID:
    workspace_id = uuid.uuid4()
    db_session.add(Workspace(id=workspace_id, name="Folder Test"))
    await db_session.commit()
    return workspace_id


async def _create_folder(
    client: AsyncClient,
    workspace_id: uuid.UUID,
    name: str,
    parent_id: uuid.UUID | None = None,
) -> dict:
    response = await client.post(
        "/api/folders/",
        json={
            "workspace_id": str(workspace_id),
            "parent_id": str(parent_id) if parent_id else None,
            "name": name,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_folder_tree_and_duplicate_name(
    member_client: AsyncClient, db_session: AsyncSession
):
    workspace_id = await _create_workspace(db_session)
    root = await _create_folder(member_client, workspace_id, "Projects")
    await _create_folder(member_client, workspace_id, "Specs", uuid.UUID(root["id"]))

    response = await member_client.get(f"/api/folders/{workspace_id}")

    assert response.status_code == 200
    tree = response.json()
    assert len(tree) == 1
    assert tree[0]["name"] == "Projects"
    assert tree[0]["children"][0]["name"] == "Specs"

    duplicate = await member_client.post(
        "/api/folders/",
        json={"workspace_id": str(workspace_id), "name": "projects"},
    )
    assert duplicate.status_code == 409


@pytest.mark.asyncio
async def test_folder_move_rejects_cycles(
    member_client: AsyncClient, db_session: AsyncSession
):
    workspace_id = await _create_workspace(db_session)
    root = await _create_folder(member_client, workspace_id, "Root")
    child = await _create_folder(
        member_client, workspace_id, "Child", uuid.UUID(root["id"])
    )

    response = await member_client.patch(
        f"/api/folders/{root['id']}",
        json={"parent_id": child["id"]},
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_delete_folder_requires_move_strategy(
    member_client: AsyncClient, db_session: AsyncSession
):
    workspace_id = await _create_workspace(db_session)
    root = await _create_folder(member_client, workspace_id, "Root")
    child = await _create_folder(
        member_client, workspace_id, "Child", uuid.UUID(root["id"])
    )

    response = await member_client.delete(f"/api/folders/{root['id']}")
    assert response.status_code == 409

    response = await member_client.delete(
        f"/api/folders/{root['id']}?strategy=move_parent"
    )
    assert response.status_code == 204

    tree = await member_client.get(f"/api/folders/{workspace_id}")
    assert tree.status_code == 200
    assert tree.json()[0]["id"] == child["id"]
    assert tree.json()[0]["parent_id"] is None


@pytest.mark.asyncio
async def test_move_document_between_folders(
    member_client: AsyncClient, db_session: AsyncSession
):
    workspace_id = await _create_workspace(db_session)
    folder = await _create_folder(member_client, workspace_id, "Inbox")
    document_id = uuid.uuid4()
    db_session.add(
        Document(
            id=document_id,
            workspace_id=workspace_id,
            filename="notes.md",
            document_type="markdown",
            size_bytes=10,
            status="completed",
        )
    )
    await db_session.commit()

    response = await member_client.patch(
        f"/api/documents/{document_id}",
        json={"folder_id": folder["id"]},
    )

    assert response.status_code == 200
    assert response.json()["folder_id"] == folder["id"]

    response = await member_client.patch(
        f"/api/documents/{document_id}",
        json={"folder_id": None},
    )

    assert response.status_code == 200
    assert response.json()["folder_id"] is None


@pytest.mark.asyncio
async def test_viewer_can_list_but_not_create(
    viewer_client: AsyncClient, db_session: AsyncSession
):
    workspace_id = await _create_workspace(db_session)

    listed = await viewer_client.get(f"/api/folders/{workspace_id}")
    assert listed.status_code == 200

    created = await viewer_client.post(
        "/api/folders/",
        json={"workspace_id": str(workspace_id), "name": "Nope"},
    )
    assert created.status_code == 403
