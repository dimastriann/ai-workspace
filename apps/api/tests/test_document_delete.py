"""Tests for document deletion."""

import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import (
    AuditLog,
    Document,
    DocumentChunk,
    DocumentConversion,
    Workspace,
)


async def _create_workspace(db_session: AsyncSession) -> Workspace:
    workspace = Workspace(id=uuid.uuid4(), name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    return workspace


async def test_member_can_delete_document(
    member_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    workspace = await _create_workspace(db_session)

    upload = await member_client.post(
        f"/api/documents/upload/{workspace.id}",
        files={"file": ("notes.txt", b"hello world", "text/plain")},
    )
    assert upload.status_code == 200
    document_id = uuid.UUID(upload.json()["document_id"])

    db_session.add(
        DocumentChunk(
            id=uuid.uuid4(),
            document_id=document_id,
            workspace_id=workspace.id,
            ordinal=0,
            content="hello world",
        )
    )
    db_session.add(
        DocumentConversion(
            id=uuid.uuid4(),
            document_id=document_id,
            status="completed",
            format="markdown",
        )
    )
    await db_session.commit()

    stored_files = list((tmp_path / "uploads").rglob("*notes.txt"))
    assert stored_files

    response = await member_client.delete(f"/api/documents/{document_id}")

    assert response.status_code == 204
    assert await db_session.get(Document, document_id) is None

    chunks = (
        (
            await db_session.execute(
                select(DocumentChunk).where(DocumentChunk.document_id == document_id)
            )
        )
        .scalars()
        .all()
    )
    assert chunks == []
    conversions = (
        (
            await db_session.execute(
                select(DocumentConversion).where(
                    DocumentConversion.document_id == document_id
                )
            )
        )
        .scalars()
        .all()
    )
    assert conversions == []
    assert not stored_files[0].exists()

    audit = (
        (
            await db_session.execute(
                select(AuditLog).where(AuditLog.action == "documents.delete")
            )
        )
        .scalars()
        .all()
    )
    assert audit


async def test_delete_missing_document(member_client: AsyncClient) -> None:
    response = await member_client.delete(f"/api/documents/{uuid.uuid4()}")

    assert response.status_code == 404


async def test_viewer_cannot_delete(viewer_client: AsyncClient) -> None:
    response = await viewer_client.delete(f"/api/documents/{uuid.uuid4()}")

    assert response.status_code == 403


async def test_delete_requires_auth(client: AsyncClient) -> None:
    response = await client.delete(f"/api/documents/{uuid.uuid4()}")

    assert response.status_code == 401
