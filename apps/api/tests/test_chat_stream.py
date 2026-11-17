"""Tests for the provider-backed chat stream."""

import uuid
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import ChatMessage, ChatSession, Workspace
from app.models.enums import Role
from app.services.agent_provider import ProviderEvent, ToolCall
from app.services.auth_service import auth_service
from app.services.chat_service import ChatService
from app.services.tools import ToolSpec


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


class ToolProvider:
    def __init__(self, turns: list[list[ProviderEvent]]) -> None:
        self._turns = turns

    async def stream(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> AsyncGenerator[ProviderEvent]:
        del messages, tools
        for event in self._turns.pop(0):
            yield event


async def test_chat_can_call_mcp_tools(db_session: AsyncSession, monkeypatch) -> None:
    workspace = Workspace(id=uuid.uuid4(), name="Test")
    db_session.add(workspace)
    await db_session.commit()
    session = ChatSession(
        id=uuid.uuid4(), workspace_id=workspace.id, title="Tool Conversation"
    )
    db_session.add(session)
    await db_session.commit()

    seen: list[dict[str, Any]] = []

    async def handler(_db, _workspace_id, arguments):
        seen.append(arguments)
        return "GitHub result"

    spec = ToolSpec(
        name="mcp__GitHub__list_issues",
        description="List issues",
        parameters={"type": "object", "properties": {}},
        permission="mcp",
        handler=handler,
    )

    async def fake_list_tools(_db):
        return [spec]

    monkeypatch.setattr(
        "app.services.chat_service.mcp_service.list_tool_specs", fake_list_tools
    )

    provider = ToolProvider(
        [
            [
                ProviderEvent(
                    type="tool_calls",
                    tool_calls=[
                        ToolCall(
                            id="call-1",
                            name="mcp__GitHub__list_issues",
                            arguments={},
                        )
                    ],
                ),
                ProviderEvent(type="done"),
            ],
            [
                ProviderEvent(type="token", content="Here are your issues."),
                ProviderEvent(type="done"),
            ],
        ]
    )

    service = ChatService(provider=provider)
    tokens = [
        token
        async for token in service.chat_stream(
            "List issues", session.id, workspace.id, db_session, context=""
        )
    ]

    assert seen == [{}]
    assert "".join(tokens) == "Here are your issues."


async def test_chat_filters_session_disabled_mcp_tools(
    db_session: AsyncSession, monkeypatch
) -> None:
    workspace = Workspace(id=uuid.uuid4(), name="Test")
    db_session.add(workspace)
    await db_session.commit()
    session = ChatSession(id=uuid.uuid4(), workspace_id=workspace.id, title="Filtered")
    db_session.add(session)
    await db_session.commit()

    seen: list[list[dict[str, Any]]] = []

    class RecordingProvider(FakeProvider):
        async def stream(
            self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
        ) -> AsyncGenerator[ProviderEvent]:
            seen.append(tools)
            async for event in super().stream(messages, tools):
                yield event

    async def handler(*args, **kwargs) -> str:
        return "unused"

    spec = ToolSpec(
        name="mcp__GitHub__list_issues",
        description="List issues",
        parameters={"type": "object", "properties": {}},
        permission="mcp",
        handler=handler,
    )

    async def fake_list_tools(_db):
        return [spec]

    monkeypatch.setattr(
        "app.services.chat_service.mcp_service.list_tool_specs", fake_list_tools
    )

    service = ChatService(provider=RecordingProvider(["ok"]))
    _ = [
        token
        async for token in service.chat_stream(
            "Hi",
            session.id,
            workspace.id,
            db_session,
            context="",
            disabled_mcp_tools=[spec.name],
        )
    ]

    assert seen
    tool_names = {tool.get("function", {}).get("name") for tool in seen[0]}
    assert "mcp__GitHub__list_issues" not in tool_names


async def test_regenerate_replaces_last_assistant(db_session: AsyncSession) -> None:
    workspace = Workspace(id=uuid.uuid4(), name="Test")
    db_session.add(workspace)
    await db_session.commit()
    user = await auth_service.create_user(
        email=f"regen-{uuid.uuid4()}@example.com",
        password="password123",
        role=Role.MEMBER,
        db=db_session,
    )
    session = ChatSession(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        user_id=user.id,
        title="Regenerate",
    )
    db_session.add(session)
    db_session.add(ChatMessage(session_id=session.id, role="user", content="Question"))
    db_session.add(
        ChatMessage(session_id=session.id, role="assistant", content="Old answer")
    )
    await db_session.commit()

    service = ChatService(provider=FakeProvider(["New answer"]))
    tokens = [
        token
        async for token in service.regenerate_stream(session.id, db_session, user.id)
    ]
    assert "".join(tokens) == "New answer"

    refreshed = await service.get_session(session.id, user.id, db_session)
    assert [message.content for message in refreshed.messages] == [
        "Question",
        "New answer",
    ]


async def test_edit_message_truncates_later_turns(db_session: AsyncSession) -> None:
    workspace = Workspace(id=uuid.uuid4(), name="Test")
    db_session.add(workspace)
    await db_session.commit()
    user = await auth_service.create_user(
        email=f"edit-{uuid.uuid4()}@example.com",
        password="password123",
        role=Role.MEMBER,
        db=db_session,
    )
    session = ChatSession(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        user_id=user.id,
        title="Edit",
    )
    db_session.add(session)
    original = ChatMessage(
        session_id=session.id, role="user", content="Original question"
    )
    db_session.add(original)
    db_session.add(
        ChatMessage(session_id=session.id, role="assistant", content="Old answer")
    )
    await db_session.commit()

    service = ChatService(provider=FakeProvider(["Edited answer"]))
    tokens = [
        token
        async for token in service.edit_message_stream(
            session.id, original.id, "Edited question", db_session, user.id
        )
    ]
    assert "".join(tokens) == "Edited answer"

    refreshed = await service.get_session(session.id, user.id, db_session)
    assert [message.content for message in refreshed.messages] == [
        "Edited question",
        "Edited answer",
    ]
