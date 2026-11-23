"""Tests for chat session history and ownership."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import ChatMessage, ChatSession, Workspace
from app.models.enums import Role
from app.services.auth_service import auth_service
from app.services.chat_service import chat_service


@pytest.mark.asyncio
async def test_chat_session_history(
    member_client: AsyncClient, db_session: AsyncSession
) -> None:
    member = await auth_service.get_user_by_email("member@example.com", db_session)
    assert member is not None
    workspace = Workspace(id=uuid.uuid4(), name="Chat Test")
    db_session.add(workspace)
    await db_session.commit()

    session = ChatSession(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        user_id=member.id,
        title="First conversation",
    )
    db_session.add(session)
    db_session.add(
        ChatMessage(
            id=uuid.uuid4(),
            session_id=session.id,
            role="user",
            content="Hello there",
        )
    )
    await db_session.commit()

    listed = await member_client.get(
        "/api/chat/sessions", params={"workspace_id": str(workspace.id)}
    )
    assert listed.status_code == 200
    assert listed.json()[0]["title"] == "First conversation"
    assert listed.json()[0]["message_count"] == 1

    search = await member_client.get("/api/chat/sessions", params={"q": "Hello"})
    assert search.status_code == 200
    assert len(search.json()) == 1
    missing = await member_client.get("/api/chat/sessions", params={"q": "absent"})
    assert missing.json() == []

    detail = await member_client.get(f"/api/chat/sessions/{session.id}")
    assert detail.status_code == 200
    assert detail.json()["messages"][0]["content"] == "Hello there"

    renamed = await member_client.patch(
        f"/api/chat/sessions/{session.id}", json={"title": "Renamed"}
    )
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Renamed"

    deleted = await member_client.delete(f"/api/chat/sessions/{session.id}")
    assert deleted.status_code == 204
    assert (
        await member_client.get(f"/api/chat/sessions/{session.id}")
    ).status_code == 404


@pytest.mark.asyncio
async def test_chat_sessions_are_private(
    member_client: AsyncClient, db_session: AsyncSession
) -> None:
    other = await auth_service.create_user(
        email="chat-other@example.com",
        password="password123",
        role=Role.MEMBER,
        db=db_session,
    )
    session = ChatSession(
        id=uuid.uuid4(),
        workspace_id=None,
        user_id=other.id,
        title="Private",
    )
    db_session.add(session)
    await db_session.commit()

    assert (
        await member_client.get(f"/api/chat/sessions/{session.id}")
    ).status_code == 404


@pytest.mark.asyncio
async def test_chat_stream_does_not_reuse_foreign_session_id(
    member_client: AsyncClient, db_session: AsyncSession
) -> None:
    member = await auth_service.get_user_by_email("member@example.com", db_session)
    other = await auth_service.create_user(
        email="chat-owner@example.com",
        password="password123",
        role=Role.MEMBER,
        db=db_session,
    )
    assert member is not None
    foreign = ChatSession(
        id=uuid.uuid4(),
        workspace_id=None,
        user_id=other.id,
        title="Not yours",
    )
    db_session.add(foreign)
    await db_session.commit()

    created = await chat_service.get_or_create_session(
        foreign.id, None, db_session, user_id=member.id
    )
    assert created.id != foreign.id
    assert created.user_id == member.id


@pytest.mark.asyncio
async def test_chat_models_and_session_model(
    member_client: AsyncClient, db_session: AsyncSession
) -> None:
    models = await member_client.get("/api/chat/models")
    assert models.status_code == 200
    body = models.json()
    assert body["models"]
    assert body["default"] in body["models"]

    member = await auth_service.get_user_by_email("member@example.com", db_session)
    assert member is not None
    session = ChatSession(
        id=uuid.uuid4(),
        workspace_id=None,
        user_id=member.id,
        title="Model test",
        model=body["default"],
    )
    db_session.add(session)
    await db_session.commit()

    listed = await member_client.get("/api/chat/sessions")
    assert listed.status_code == 200
    assert listed.json()[0]["model"] == body["default"]

    updated = await member_client.patch(
        f"/api/chat/sessions/{session.id}",
        json={"model": body["models"][-1]},
    )
    assert updated.status_code == 200
    assert updated.json()["model"] == body["models"][-1]


@pytest.mark.asyncio
async def test_chat_attachment_upload_and_context(
    member_client: AsyncClient, db_session: AsyncSession
) -> None:
    uploaded = await member_client.post(
        "/api/chat/attachments",
        files={"file": ("notes.txt", b"unique attachment context", "text/plain")},
    )
    assert uploaded.status_code == 200, uploaded.text
    body = uploaded.json()
    assert body["filename"] == "notes.txt"
    assert body["characters"] > 0

    member = await auth_service.get_user_by_email("member@example.com", db_session)
    assert member is not None
    context = await chat_service.attachment_context([body["id"]], member.id, db_session)
    assert "unique attachment context" in context

    unsupported = await member_client.post(
        "/api/chat/attachments",
        files={"file": ("image.exe", b"binary", "application/octet-stream")},
    )
    assert unsupported.status_code == 415


@pytest.mark.asyncio
async def test_chat_image_attachment_upload_and_parts(
    member_client: AsyncClient, db_session: AsyncSession, tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr("app.services.storage.UPLOADS_ROOT", tmp_path)
    png_bytes = b"\x89PNG\r\n\x1a\nfake-image-bytes"

    uploaded = await member_client.post(
        "/api/chat/attachments",
        files={"file": ("shot.png", png_bytes, "image/png")},
    )
    assert uploaded.status_code == 200, uploaded.text
    body = uploaded.json()
    assert body["is_image"] is True
    assert body["characters"] == 0

    member = await auth_service.get_user_by_email("member@example.com", db_session)
    assert member is not None

    # Images contribute no text context but do produce provider image parts.
    context = await chat_service.attachment_context([body["id"]], member.id, db_session)
    assert context == ""
    parts = await chat_service.attachment_image_parts(
        [body["id"]], member.id, db_session
    )
    assert len(parts) == 1
    assert parts[0]["type"] == "image_url"
    assert parts[0]["image_url"]["url"].startswith("data:image/png;base64,")

    # Owner can download the stored bytes back.
    served = await member_client.get(f"/api/chat/attachments/{body['id']}/file")
    assert served.status_code == 200
    assert served.headers["content-type"] == "image/png"
    assert served.content == png_bytes


@pytest.mark.asyncio
async def test_chat_image_attachment_owner_only(
    member_client: AsyncClient, db_session: AsyncSession
) -> None:
    uploaded = await member_client.post(
        "/api/chat/attachments",
        files={"file": ("shot.png", b"\x89PNG-data", "image/png")},
    )
    assert uploaded.status_code == 200, uploaded.text
    attachment_id = uploaded.json()["id"]

    # Sign in as a different user on the same client; ownership must fail.
    await auth_service.create_user(
        email="other@example.com",
        password="password123",
        role=Role.MEMBER,
        db=db_session,
    )
    switched = await member_client.post(
        "/api/auth/login",
        json={"email": "other@example.com", "password": "password123"},
    )
    assert switched.status_code == 200

    denied = await member_client.get(f"/api/chat/attachments/{attachment_id}/file")
    assert denied.status_code == 404
