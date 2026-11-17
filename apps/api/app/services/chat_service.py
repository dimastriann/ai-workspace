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

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ChatSessionNotFoundError, ChatValidationError
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

        async for token in self._stream_completion(
            messages,
            session_id,
            workspace_id,
            db,
            user_id,
            disabled_mcp_tools,
        ):
            yield token

    async def regenerate_stream(
        self,
        session_id: UUID,
        db: AsyncSession,
        user_id: UUID,
        disabled_mcp_tools: list[str] | None = None,
    ) -> AsyncGenerator[str]:
        """Replace the latest assistant message with a fresh response."""
        session = await self.get_session(session_id, user_id, db)
        messages = list(session.messages)
        if not messages or messages[-1].role != "assistant":
            raise ChatValidationError("Nothing to regenerate")

        await db.delete(messages[-1])
        await db.commit()
        messages = messages[:-1]

        last_user = next(
            (message for message in reversed(messages) if message.role == "user"),
            None,
        )
        if last_user is None:
            raise ChatValidationError("No user message to regenerate from")

        context, _sources = (
            await self.build_context(last_user.content, session.workspace_id, db)
            if session.workspace_id
            else ("", [])
        )
        system_msg = self._system_prompt(context)
        history = self._history_from_messages(messages)
        prompt = [
            {"role": "system", "content": system_msg},
            *history,
        ]

        async for token in self._stream_completion(
            prompt,
            session_id,
            session.workspace_id,
            db,
            user_id,
            disabled_mcp_tools,
        ):
            yield token

    async def edit_message_stream(
        self,
        session_id: UUID,
        message_id: UUID,
        new_content: str,
        db: AsyncSession,
        user_id: UUID,
        disabled_mcp_tools: list[str] | None = None,
    ) -> AsyncGenerator[str]:
        """Edit a user message, truncate later turns, and answer it again."""
        session = await self.get_session(session_id, user_id, db)
        messages = list(session.messages)
        target_index = next(
            (
                index
                for index, message in enumerate(messages)
                if message.id == message_id and message.role == "user"
            ),
            None,
        )
        if target_index is None:
            raise ChatValidationError("User message not found")

        for message in messages[target_index + 1 :]:
            await db.delete(message)
        messages[target_index].content = new_content.strip()
        session.updated_at = datetime.now(UTC).replace(tzinfo=None)
        await db.commit()

        kept = messages[: target_index + 1]
        context, _sources = (
            await self.build_context(new_content, session.workspace_id, db)
            if session.workspace_id
            else ("", [])
        )
        prompt = [
            {"role": "system", "content": self._system_prompt(context)},
            *self._history_from_messages(kept),
        ]

        async for token in self._stream_completion(
            prompt,
            session_id,
            session.workspace_id,
            db,
            user_id,
            disabled_mcp_tools,
        ):
            yield token

    async def _stream_completion(
        self,
        messages: list[dict[str, Any]],
        session_id: UUID,
        workspace_id: UUID | None,
        db: AsyncSession,
        user_id: UUID | None,
        disabled_mcp_tools: list[str] | None,
    ) -> AsyncGenerator[str]:
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
        session = await db.get(ChatSession, session_id)
        if session is not None:
            session.updated_at = datetime.now(UTC).replace(tzinfo=None)
        await db.commit()

    @staticmethod
    def _system_prompt(context: str) -> str:
        system_msg = "You are a helpful AI assistant in the AI Workspace platform."
        if context:
            system_msg += (
                "\n\nUse the following context from the documents to answer "
                f"the user if relevant:\n{context}"
            )
        return system_msg

    @staticmethod
    def _history_from_messages(messages: list[ChatMessage]) -> list[dict[str, Any]]:
        return [
            {
                "role": "user" if item.role == "user" else "assistant",
                "content": item.content,
            }
            for item in messages[-10:]
        ]

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
        self,
        workspace_id: UUID | None,
        user_id: UUID,
        db: AsyncSession,
        query: str | None = None,
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
        if query and query.strip():
            pattern = f"%{query.strip()}%"
            statement = statement.where(
                or_(
                    ChatSession.title.ilike(pattern),
                    ChatSession.id.in_(
                        select(ChatMessage.session_id).where(
                            ChatMessage.content.ilike(pattern)
                        )
                    ),
                )
            )
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
