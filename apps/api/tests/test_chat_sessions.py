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
