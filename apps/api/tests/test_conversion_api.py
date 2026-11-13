"""Tests for conversion endpoints and the conversion job."""

import io
import uuid
import zipfile
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Document, Workspace
from app.tasks import worker
from app.tasks.conversion import process_conversion


async def _upload(client: AsyncClient, workspace_id: uuid.UUID) -> str:
    response = await client.post(
        f"/api/documents/upload/{workspace_id}",
        files={"file": ("notes.txt", b"hello conversion", "text/plain")},
    )
    assert response.status_code == 200
    return response.json()["document_id"]


async def _create_workspace(db_session: AsyncSession) -> Workspace:
    workspace = Workspace(id=uuid.uuid4(), name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    return workspace


def test_worker_registers_conversion_handler() -> None:
    assert worker.HANDLERS["document.convert"] is process_conversion


async def test_conversion_flow(
    member_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    workspace = await _create_workspace(db_session)
    document_id = await _upload(member_client, workspace.id)

    start = await member_client.post(
        f"/api/documents/{document_id}/convert",
        json={"include_images": False},
    )
    assert start.status_code == 202
    conversion_id = start.json()["id"]
    assert start.json()["status"] == "pending"

    status_response = await member_client.get(
        f"/api/documents/{document_id}/conversion"
    )
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "pending"

    await process_conversion(db_session, {"conversion_id": conversion_id})

    completed = await member_client.get(f"/api/documents/{document_id}/conversion")
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"

    markdown = await member_client.get(f"/api/documents/{document_id}/markdown")
    assert markdown.status_code == 200
    assert "hello conversion" in markdown.text

    archive = await member_client.get(f"/api/documents/{document_id}/markdown.zip")
    assert archive.status_code == 200
    with zipfile.ZipFile(io.BytesIO(archive.content)) as bundle:
        assert "document.md" in bundle.namelist()


async def test_download_before_conversion_returns_404(
    member_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    workspace = await _create_workspace(db_session)
    document_id = await _upload(member_client, workspace.id)

    response = await member_client.get(f"/api/documents/{document_id}/markdown")

    assert response.status_code == 404


async def test_viewer_cannot_start_conversion(viewer_client: AsyncClient) -> None:
    response = await viewer_client.post(
        f"/api/documents/{uuid.uuid4()}/convert", json={"include_images": False}
    )

    assert response.status_code == 403


async def test_convert_missing_document(member_client: AsyncClient) -> None:
    response = await member_client.post(
        f"/api/documents/{uuid.uuid4()}/convert", json={"include_images": False}
    )

    assert response.status_code == 404


async def test_conversion_job_marks_errors(
    member_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    workspace = await _create_workspace(db_session)
    document_id = await _upload(member_client, workspace.id)

    start = await member_client.post(
        f"/api/documents/{document_id}/convert",
        json={"include_images": False},
    )
    conversion_id = start.json()["id"]

    document = await db_session.get(Document, uuid.UUID(document_id))
    assert document is not None
    source = next((tmp_path / "uploads").rglob("*notes.txt"))
    source.unlink()

    with pytest.raises(FileNotFoundError):
        await process_conversion(db_session, {"conversion_id": conversion_id})

    status_response = await member_client.get(
        f"/api/documents/{document_id}/conversion"
    )
    assert status_response.json()["status"] == "error"
