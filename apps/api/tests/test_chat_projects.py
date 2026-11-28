"""Tests for project-scoped chat sessions, instructions, and retrieval."""

import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import (
    ChatProject,
    ChatSession,
    Document,
    DocumentChunk,
    Workspace,
)
from app.services.agent_provider import ProviderEvent
from app.services.chat_service import ChatService
from app.services.retrieval import retrieval_service


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


async def _project_session(
    db: AsyncSession, *, instructions: str, memory_mode: str
) -> tuple[Workspace, ChatSession, ChatProject]:
    workspace = Workspace(id=uuid.uuid4(), name="WS")
    db.add(workspace)
    await db.commit()
    project = ChatProject(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        name="Research",
        instructions=instructions,
        memory_mode=memory_mode,
    )
    db.add(project)
    await db.commit()
    session = ChatSession(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        project_id=project.id,
        title="Scoped",
    )
    db.add(session)
    await db.commit()
    return workspace, session, project


async def test_project_instructions_reach_system_prompt(
    db_session: AsyncSession,
) -> None:
    workspace, session, _project = await _project_session(
        db_session, instructions="Always cite sources.", memory_mode="workspace"
    )

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
            "Hi", session.id, workspace.id, db_session, context=""
        )
    ]

    system = seen[0][0]["content"]
    assert "Project instructions:" in system
    assert "Always cite sources." in system


async def test_project_mode_restricts_retrieval(db_session: AsyncSession) -> None:
    workspace, session, project = await _project_session(
        db_session, instructions="", memory_mode="project"
    )

    document = Document(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        filename="project.md",
        document_type="markdown",
        size_bytes=3,
    )
    document.project_id = project.id
    other = Document(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        filename="other.md",
        document_type="markdown",
        size_bytes=3,
    )
    db_session.add_all([document, other])
    await db_session.commit()
    db_session.add_all(
        [
            DocumentChunk(
                document_id=document.id,
                workspace_id=workspace.id,
                ordinal=0,
                content="project knowledge",
            ),
            DocumentChunk(
                document_id=other.id,
                workspace_id=workspace.id,
                ordinal=0,
                content="workspace knowledge",
            ),
        ]
    )
    await db_session.commit()

    scoped_project, scoped_only = await ChatService().retrieval_scope(
        session, db_session
    )
    assert scoped_project == project.id
    assert scoped_only is True

    chunks = await retrieval_service.search(
        "knowledge",
        workspace.id,
        db_session,
        project_id=scoped_project,
        project_only=scoped_only,
    )
    assert [chunk.content for chunk in chunks] == ["project knowledge"]

    # Workspace mode sees everything.
    unscoped = await retrieval_service.search("knowledge", workspace.id, db_session)
    assert {chunk.content for chunk in unscoped} == {
        "project knowledge",
        "workspace knowledge",
    }


@pytest.mark.asyncio
async def test_session_without_project_is_unscoped(
    db_session: AsyncSession,
) -> None:
    workspace = Workspace(id=uuid.uuid4(), name="WS")
    db_session.add(workspace)
    await db_session.commit()
    session = ChatSession(id=uuid.uuid4(), workspace_id=workspace.id, title="Plain")
    db_session.add(session)
    await db_session.commit()

    service = ChatService()
    project_id, project_only = await service.retrieval_scope(session, db_session)

    assert project_id is None
    assert project_only is False
    assert await service.project_instructions(session, db_session) == ""
