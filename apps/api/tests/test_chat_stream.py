"""Tests for the provider-backed chat stream."""

import uuid
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import ChatMessage, ChatSession, Workspace
from app.services.agent_provider import ProviderEvent
from app.services.chat_service import ChatService


class FakeProvider:
    def __init__(self, tokens: list[str]) -> None:
        self._tokens = tokens

    async def stream(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> AsyncGenerator[ProviderEvent]:
        del messages, tools
        for token in self._tokens:
            yield ProviderEvent(type="token", content=token)
        yield ProviderEvent(type="done")


async def test_chat_stream_persists_messages(db_session: AsyncSession) -> None:
    workspace = Workspace(id=uuid.uuid4(), name="Test")
    db_session.add(workspace)
    await db_session.commit()

    session = ChatSession(
        id=uuid.uuid4(), workspace_id=workspace.id, title="Test Conversation"
    )
    db_session.add(session)
    await db_session.commit()

    service = ChatService(provider=FakeProvider(["Hello", " world"]))
    tokens = [
        token
        async for token in service.chat_stream(
            "Hi", session.id, workspace.id, db_session, context=""
        )
    ]

    assert "".join(tokens) == "Hello world"

    result = await db_session.execute(
        select(ChatMessage).where(ChatMessage.session_id == session.id)
    )
    rows = result.scalars().all()
    by_role = {row.role: row.content for row in rows}
    assert by_role == {"user": "Hi", "assistant": "Hello world"}


async def test_chat_stream_includes_history(db_session: AsyncSession) -> None:
    workspace = Workspace(id=uuid.uuid4(), name="Test")
    db_session.add(workspace)
    await db_session.commit()

    session = ChatSession(
        id=uuid.uuid4(), workspace_id=workspace.id, title="Test Conversation"
    )
    db_session.add(session)
    await db_session.commit()
    db_session.add(
        ChatMessage(session_id=session.id, role="user", content="Earlier question")
    )
    await db_session.commit()

    seen: list[list[dict[str, Any]]] = []

    class RecordingProvider(FakeProvider):
        async def stream(
            self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
        ) -> AsyncGenerator[ProviderEvent]:
            seen.append(messages)
            async for event in super().stream(messages, tools):
                yield event

    service = ChatService(provider=RecordingProvider(["ok"]))
    _ = [
        token
        async for token in service.chat_stream(
            "Now", session.id, workspace.id, db_session, context=""
        )
    ]

    assert seen
    assert any(
        item["role"] == "user" and item["content"] == "Earlier question"
        for item in seen[0]
    )
