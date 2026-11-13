"""Tests for upload size and type validation."""

import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import Workspace


async def _create_workspace(db_session: AsyncSession) -> Workspace:
    workspace = Workspace(id=uuid.uuid4(), name="Test Workspace")
    db_session.add(workspace)
    await db_session.commit()
    return workspace


async def test_rejects_unsupported_extension(
    member_client: AsyncClient, db_session: AsyncSession
) -> None:
    workspace = await _create_workspace(db_session)

    response = await member_client.post(
        f"/api/documents/upload/{workspace.id}",
        files={"file": ("evil.exe", b"payload", "application/octet-stream")},
    )

    assert response.status_code == 415


async def test_rejects_oversized_file(
    member_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = await _create_workspace(db_session)
    monkeypatch.setattr(settings, "max_upload_mb", 0)

    response = await member_client.post(
        f"/api/documents/upload/{workspace.id}",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 413


async def test_rejects_missing_workspace(
    member_client: AsyncClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    response = await member_client.post(
        f"/api/documents/upload/{uuid.uuid4()}",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 404
    assert not (tmp_path / "uploads").exists()


async def test_accepts_allowed_file(
    member_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    workspace = await _create_workspace(db_session)

    response = await member_client.post(
        f"/api/documents/upload/{workspace.id}",
        files={"file": ("notes.txt", b"hello world", "text/plain")},
    )

    assert response.status_code == 200
    assert response.json()["document_type"] == "text"
    assert list((tmp_path / "uploads").rglob("*notes.txt"))
