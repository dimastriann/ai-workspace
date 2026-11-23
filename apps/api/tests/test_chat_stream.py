"""Tests for the provider-backed chat stream."""

import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import ChatAttachment, ChatMessage, ChatSession, Workspace
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


async def test_regenerate_creates_branch(db_session: AsyncSession) -> None:
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
    question = ChatMessage(
        id=uuid.uuid4(),
        session_id=session.id,
        role="user",
        content="Question",
    )
    old_answer = ChatMessage(
        id=uuid.uuid4(),
        session_id=session.id,
        role="assistant",
        content="Old answer",
        parent_id=question.id,
    )
    db_session.add(question)
    db_session.add(old_answer)
    session.active_leaf_id = old_answer.id
    await db_session.commit()

    service = ChatService(provider=FakeProvider(["New answer"]))
    tokens = [
        token
        async for token in service.regenerate_stream(session.id, db_session, user.id)
    ]
    assert "".join(tokens) == "New answer"

    refreshed = await service.get_session(session.id, user.id, db_session)
    active = service._active_messages(refreshed)
    assert [message.content for message in active] == ["Question", "New answer"]
    assert len(refreshed.messages) == 3
    siblings = service._siblings_for_parent(refreshed, question.id)
    assert {message.content for message in siblings} == {"Old answer", "New answer"}
    assert refreshed.active_leaf_id is not None

    old_sibling = next(
        message for message in siblings if message.content == "Old answer"
    )
    switched = await service.switch_branch(
        old_sibling.id, siblings.index(old_sibling), user.id, db_session
    )
    assert switched.active_leaf_id == old_sibling.id
    active = service._active_messages(switched)
    assert [message.content for message in active] == ["Question", "Old answer"]


async def test_edit_message_creates_branch(db_session: AsyncSession) -> None:
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
        id=uuid.uuid4(),
        session_id=session.id,
        role="user",
        content="Original question",
    )
    old_answer = ChatMessage(
        id=uuid.uuid4(),
        session_id=session.id,
        role="assistant",
        content="Old answer",
        parent_id=original.id,
    )
    db_session.add(original)
    db_session.add(old_answer)
    session.active_leaf_id = old_answer.id
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
    active = service._active_messages(refreshed)
    assert [message.content for message in active] == [
        "Edited question",
        "Edited answer",
    ]
    assert len(refreshed.messages) == 4
    assert refreshed.active_leaf_id is not None
    original = next(
        message
        for message in refreshed.messages
        if message.content == "Original question"
    )
    siblings = service._siblings_for_parent(refreshed, original.parent_id)
    assert {message.content for message in siblings} == {
        "Original question",
        "Edited question",
    }
    old_branch = next(
        message for message in refreshed.messages if message.content == "Old answer"
    )
    switched = await service.switch_branch(
        old_branch.id,
        service._siblings_for_parent(refreshed, old_branch.parent_id).index(old_branch),
        user.id,
        db_session,
    )
    assert switched.active_leaf_id == old_branch.id
    active = service._active_messages(switched)
    assert [message.content for message in active] == [
        "Original question",
        "Old answer",
    ]


async def test_edit_message_can_replace_attachments(db_session: AsyncSession) -> None:
    workspace = Workspace(id=uuid.uuid4(), name="Test")
    db_session.add(workspace)
    await db_session.commit()
    user = await auth_service.create_user(
        email=f"edit-attach-{uuid.uuid4()}@example.com",
        password="password123",
        role=Role.MEMBER,
        db=db_session,
    )
    session = ChatSession(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        user_id=user.id,
        title="Edit attachments",
    )
    db_session.add(session)
    original = ChatMessage(
        id=uuid.uuid4(),
        session_id=session.id,
        role="user",
        content="With attachments",
        attachment_ids=json.dumps([str(uuid.uuid4()), str(uuid.uuid4())]),
    )
    db_session.add(original)
    await db_session.commit()

    keep_id = str(uuid.uuid4())
    replacement = ChatAttachment(
        id=uuid.uuid4(),
        user_id=user.id,
        filename="kept.png",
        size_bytes=3,
        content_text="",
        is_image=True,
    )
    db_session.add(replacement)
    await db_session.commit()

    service = ChatService(provider=FakeProvider(["Answer"]))
    tokens = [
        token
        async for token in service.edit_message_stream(
            session.id,
            original.id,
            "Edited with fewer attachments",
            db_session,
            user.id,
            attachment_ids=[keep_id, str(replacement.id)],
        )
    ]
    assert "".join(tokens) == "Answer"

    refreshed = await service.get_session(session.id, user.id, db_session)
    edited = next(
        message
        for message in refreshed.messages
        if message.content == "Edited with fewer attachments"
    )
    assert json.loads(edited.attachment_ids) == [keep_id, str(replacement.id)]
    # The original branch keeps its own attachments.
    assert json.loads(original.attachment_ids) != json.loads(edited.attachment_ids)
