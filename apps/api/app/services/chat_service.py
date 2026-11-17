"""
AI Workspace API — Chat Service

Orchestrates the conversational AI logic:
1. Session management (PostgreSQL history).
2. Lexical context retrieval (Postgres full-text search).
3. Streaming response generation through the shared provider.
"""

import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ChatSessionNotFoundError
from app.models.database import ChatMessage, ChatSession
from app.services.agent_provider import AgentProvider, ToolCall, get_provider
from app.services.agent_service import DEFAULT_PERMISSIONS
from app.services.audit_service import audit_service
from app.services.mcp_service import mcp_service
from app.services.retrieval import retrieval_service
from app.services.tools import ToolSpec, tool_registry

MAX_CHAT_TOOL_ROUNDS = 4


class ChatService:
    def __init__(self, provider: AgentProvider | None = None):
        self._provider = provider or get_provider()

    async def get_or_create_session(
        self,
        session_id: UUID | None,
        workspace_id: UUID | None,
        db: AsyncSession,
        user_id: UUID | None = None,
    ) -> ChatSession:
        """Fetch an existing owned session or create a new one."""
        if session_id:
            result = await db.execute(
                select(ChatSession).where(ChatSession.id == session_id)
            )
            session = result.scalar_one_or_none()
            if session and (user_id is None or session.user_id in (None, user_id)):
                if user_id is not None and session.user_id is None:
                    session.user_id = user_id
                    await db.commit()
                return session
            if session is not None:
                # Never reuse another user's session id.
                session_id = None

        new_session = ChatSession(
            id=session_id or uuid4(),
            workspace_id=workspace_id,
            user_id=user_id,
            title="New Conversation",
        )
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        return new_session

    async def build_context(
        self, query: str, workspace_id: UUID, db: AsyncSession
    ) -> tuple[str, list[dict[str, object]]]:
        """Retrieve context plus a source list for the response."""
        try:
            chunks = await retrieval_service.search(query, workspace_id, db)
        except Exception:
            return "", []

        context = "\n---\n".join(chunk.content for chunk in chunks)
        sources = [
            {
                "document_id": chunk.document_id,
                "filename": chunk.filename,
                "ordinal": chunk.ordinal,
                "snippet": chunk.content[:200],
            }
            for chunk in chunks
        ]
        return context, sources

    async def chat_stream(
        self,
        message: str,
        session_id: UUID,
        workspace_id: UUID | None,
        db: AsyncSession,
        context: str | None = None,
        user_id: UUID | None = None,
        disabled_mcp_tools: list[str] | None = None,
    ) -> AsyncGenerator[str]:
        """Stream a response, persisting the user and assistant messages."""
        if context is None:
            context = ""
            if workspace_id:
                context, _ = await self.build_context(message, workspace_id, db)

        history = await self._get_history(session_id, db)

        system_msg = "You are a helpful AI assistant in the AI Workspace platform."
        if context:
            system_msg += (
                "\n\nUse the following context from the documents to answer "
                f"the user if relevant:\n{context}"
            )

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_msg},
            *history,
            {"role": "user", "content": message},
        ]

        user_msg = ChatMessage(session_id=session_id, role="user", content=message)
        db.add(user_msg)
        session = await db.get(ChatSession, session_id)
        if session is not None:
            if session.title == "New Conversation":
                session.title = message.strip()[:80]
            session.updated_at = datetime.now(UTC).replace(tzinfo=None)
        await db.commit()

        permissions = set(DEFAULT_PERMISSIONS)
        disabled = set(disabled_mcp_tools or [])
        mcp_tools = [
            tool
            for tool in await mcp_service.list_tool_specs(db)
            if tool.name not in disabled
        ]
        if mcp_tools:
            permissions.add("mcp")
        tools = [*tool_registry.list_for(permissions), *mcp_tools]
        available = {tool.name: tool for tool in tools}
        schemas = [tool.to_openai() for tool in tools]

        full_response = ""
        for _ in range(MAX_CHAT_TOOL_ROUNDS):
            assistant_text = ""
            calls: list[ToolCall] = []

            async for event in self._provider.stream(messages, schemas):
                if event.type == "token":
                    assistant_text += event.content
                    full_response += event.content
                    yield event.content
                elif event.type == "tool_calls":
                    calls = event.tool_calls

            if not calls:
                break

            messages.append(
                {
                    "role": "assistant",
                    "content": assistant_text or None,
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.name,
                                "arguments": json.dumps(call.arguments),
                            },
                        }
                        for call in calls
                    ],
                }
            )

            for call in calls:
                output, _status = await self._run_tool(
                    db, workspace_id, call, permissions, available, user_id, session_id
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": output,
                    }
                )

        assistant_msg = ChatMessage(
            session_id=session_id, role="assistant", content=full_response
        )
        db.add(assistant_msg)
        await db.commit()

    async def _run_tool(
        self,
        db: AsyncSession,
        workspace_id: UUID | None,
        call: ToolCall,
        permissions: set[str],
        available: dict[str, ToolSpec],
        user_id: UUID | None,
        session_id: UUID,
    ) -> tuple[str, str]:
        tool = available.get(call.name)
        if tool is None or tool.permission not in permissions:
            return f"Tool not available: {call.name}", "error"
        if tool.requires_approval:
            return f"Tool requires approval: {call.name}", "error"
        if workspace_id is None and tool.name in {"search_documents"}:
            return "No workspace selected for document search", "error"

        try:
            output = await tool.handler(db, workspace_id or UUID(int=0), call.arguments)
            status = "completed"
        except Exception as exc:
            output, status = f"Tool failed: {exc}", "error"

        if tool.permission == "mcp":
            await audit_service.record(
                db,
                action="mcp.tool_call",
                actor_id=user_id,
                target=call.name,
                details={
                    "session_id": str(session_id),
                    "tool": call.name,
                    "status": status,
                },
            )
        return output, status

    async def list_sessions(
        self, workspace_id: UUID | None, user_id: UUID, db: AsyncSession
    ) -> list[tuple[ChatSession, int]]:
        """List a user's sessions with message counts."""
        statement = (
            select(ChatSession, func.count(ChatMessage.id))
            .outerjoin(ChatMessage, ChatMessage.session_id == ChatSession.id)
            .where(ChatSession.user_id == user_id)
            .group_by(ChatSession.id)
            .order_by(ChatSession.updated_at.desc())
        )
        if workspace_id is not None:
            statement = statement.where(ChatSession.workspace_id == workspace_id)
        result = await db.execute(statement)
        return [(session, int(count)) for session, count in result.all()]

    async def get_session(
        self, session_id: UUID, user_id: UUID, db: AsyncSession
    ) -> ChatSession:
        """Load an owned session with messages."""
        result = await db.execute(
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(ChatSession.id == session_id)
            .execution_options(populate_existing=True)
        )
        session = result.scalar_one_or_none()
        if session is None or session.user_id != user_id:
            raise ChatSessionNotFoundError("Chat session not found")
        return session

    async def rename_session(
        self, session_id: UUID, title: str, user_id: UUID, db: AsyncSession
    ) -> ChatSession:
        """Rename an owned session."""
        session = await self.get_session(session_id, user_id, db)
        session.title = title.strip()
        await db.commit()
        await db.refresh(session)
        return session

    async def delete_session(
        self, session_id: UUID, user_id: UUID, db: AsyncSession
    ) -> ChatSession:
        """Delete an owned session and its messages."""
        session = await self.get_session(session_id, user_id, db)
        await db.delete(session)
        await db.commit()
        return session

    async def _get_history(
        self, session_id: UUID, db: AsyncSession
    ) -> list[dict[str, Any]]:
        """Load recent message history in provider message format."""
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(10)
        )
        messages = list(result.scalars().all())
        messages.reverse()

        return [
            {
                "role": "user" if item.role == "user" else "assistant",
                "content": item.content,
            }
            for item in messages
        ]


# Singleton instance
chat_service = ChatService()
