"""
AI Workspace API — Chat Service

Orchestrates the conversational AI logic:
1. Session management (PostgreSQL history).
2. Lexical context retrieval (Postgres full-text search).
3. Streaming response generation through the shared provider.
"""

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.errors import (
    ChatSessionNotFoundError,
    ChatValidationError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from app.models.database import ChatAttachment, ChatMessage, ChatSession
from app.services.agent_provider import AgentProvider, ToolCall, get_provider
from app.services.agent_service import DEFAULT_PERMISSIONS
from app.services.audit_service import audit_service
from app.services.mcp_service import mcp_service
from app.services.parsing import extract_text
from app.services.retrieval import retrieval_service
from app.services.tools import ToolSpec, tool_registry

MAX_CHAT_TOOL_ROUNDS = 4


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


MAX_ATTACHMENT_CHARS = 100_000


class ChatService:
    def __init__(self, provider: AgentProvider | None = None):
        self._custom_provider = provider is not None
        self._provider = provider or get_provider()

    async def get_or_create_session(
        self,
        session_id: UUID | None,
        workspace_id: UUID | None,
        db: AsyncSession,
        user_id: UUID | None = None,
        model: str | None = None,
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
                if model is not None:
                    session.model = model
                if user_id is not None or model is not None:
                    await db.commit()
                return session
            if session is not None:
                # Never reuse another user's session id.
                session_id = None

        new_session = ChatSession(
            id=session_id or uuid4(),
            workspace_id=workspace_id,
            user_id=user_id,
            model=model,
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

    async def create_attachment(
        self, filename: str, data: bytes, user_id: UUID, db: AsyncSession
    ) -> ChatAttachment:
        """Extract text from a chat attachment and persist it."""
        safe_name = Path(filename or "attachment").name
        suffix = Path(safe_name).suffix.lower().lstrip(".")
        if suffix not in settings.allowed_upload_extension_set:
            raise UnsupportedFileTypeError(
                f"Unsupported file type: {suffix or 'unknown'}"
            )
        if len(data) > settings.max_upload_mb * 1024 * 1024:
            raise FileTooLargeError(
                f"File exceeds the {settings.max_upload_mb} MB limit"
            )

        text = await asyncio.to_thread(extract_text, safe_name, data)
        text = text.strip()[:MAX_ATTACHMENT_CHARS]
        attachment = ChatAttachment(
            user_id=user_id,
            filename=safe_name,
            size_bytes=len(data),
            content_text=text,
        )
        db.add(attachment)
        await db.commit()
        await db.refresh(attachment)
        return attachment

    async def attachment_context(
        self, attachment_ids: list[str], user_id: UUID | None, db: AsyncSession
    ) -> str:
        """Build labeled context from owned attachments."""
        if not attachment_ids or user_id is None:
            return ""
        ids: list[uuid.UUID] = []
        for value in attachment_ids:
            try:
                ids.append(UUID(str(value)))
            except ValueError:
                continue
        if not ids:
            return ""
        result = await db.execute(
            select(ChatAttachment).where(
                ChatAttachment.id.in_(ids),
                ChatAttachment.user_id == user_id,
            )
        )
        attachments = list(result.scalars().all())
        if not attachments:
            return ""
        return "\n\n".join(
            f"Attached file: {attachment.filename}\n{attachment.content_text}"
            for attachment in attachments
        )

    @staticmethod
    def _attachment_ids(message: ChatMessage) -> list[str]:
        try:
            parsed = json.loads(message.attachment_ids or "[]")
            return [str(item) for item in parsed] if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []

    @staticmethod
    def _active_messages(session: ChatSession) -> list[ChatMessage]:
        """Return the message path for the session's active branch."""
        if session.active_leaf_id is None:
            return list(session.messages)

        by_id = {message.id: message for message in session.messages}
        leaf = by_id.get(session.active_leaf_id)
        if leaf is None:
            return list(session.messages)

        path: list[ChatMessage] = []
        current: ChatMessage | None = leaf
        while current is not None:
            path.append(current)
            current = by_id.get(current.parent_id) if current.parent_id else None
        path.reverse()
        return path

    async def switch_branch(
        self, message_id: UUID, index: int, user_id: UUID, db: AsyncSession
    ) -> ChatSession:
        """Select a sibling branch and make its latest leaf active."""
        message = await db.get(ChatMessage, message_id)
        if message is None:
            raise ChatValidationError("Message not found")
        session = await self.get_session(
            message.session_id, user_id or uuid.uuid4(), db
        )
        siblings = self._siblings_for_parent(session, message.parent_id)
        if index < 0 or index >= len(siblings):
            raise ChatValidationError("Branch out of range")
        target = siblings[index]
        session.active_leaf_id = self._branch_leaf(session, target).id
        await db.commit()
        await db.refresh(session)
        return session

    @staticmethod
    def _siblings_for_parent(
        session: ChatSession, parent_id: uuid.UUID | None
    ) -> list[ChatMessage]:
        siblings = [
            message for message in session.messages if message.parent_id == parent_id
        ]
        siblings.sort(key=lambda message: (message.created_at, message.id))
        return siblings

    @staticmethod
    def _branch_leaf(session: ChatSession, message: ChatMessage) -> ChatMessage:
        """Return the newest descendant of a message, or the message itself."""
        current = message
        while True:
            children = [
                item for item in session.messages if item.parent_id == current.id
            ]
            if not children:
                return current
            current = max(children, key=lambda item: (item.created_at, item.id))

    async def chat_stream(
        self,
        message: str,
        session_id: UUID,
        workspace_id: UUID | None,
        db: AsyncSession,
        context: str | None = None,
        user_id: UUID | None = None,
        disabled_mcp_tools: list[str] | None = None,
        model: str | None = None,
        attachment_ids: list[str] | None = None,
    ) -> AsyncGenerator[str]:
        """Stream a response, persisting the user and assistant messages."""
        session = await self.get_session(session_id, user_id, db)
        active = self._active_messages(session)
        parent = active[-1].id if active else None

        if context is None:
            context = ""
            if workspace_id:
                context, _ = await self.build_context(message, workspace_id, db)

        attachment_context = await self.attachment_context(
            attachment_ids or [], user_id, db
        )
        if attachment_context:
            context = (
                f"{context}\n\n{attachment_context}" if context else attachment_context
            )

        system_msg = self._system_prompt(context)

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_msg},
            *self._history_from_messages(active),
            {"role": "user", "content": message},
        ]

        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=message,
            attachment_ids=json.dumps(attachment_ids or []),
            parent_id=parent,
            created_at=_utcnow(),
        )
        db.add(user_msg)
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
            model,
            parent_message_id=user_msg.id,
        ):
            yield token

    async def regenerate_stream(
        self,
        session_id: UUID,
        db: AsyncSession,
        user_id: UUID,
        disabled_mcp_tools: list[str] | None = None,
    ) -> AsyncGenerator[str]:
        """Replace the active assistant response with a new branch."""
        session = await self.get_session(session_id, user_id, db)
        active = self._active_messages(session)
        if not active or active[-1].role != "assistant":
            raise ChatValidationError("Nothing to regenerate")

        last_assistant = active[-1]
        history = active[:-1]

        last_user = next(
            (message for message in reversed(history) if message.role == "user"),
            None,
        )
        if last_user is None:
            raise ChatValidationError("No user message to regenerate from")

        context, _sources = (
            await self.build_context(last_user.content, session.workspace_id, db)
            if session.workspace_id
            else ("", [])
        )
        attachment_context = await self.attachment_context(
            self._attachment_ids(last_user), user_id, db
        )
        if attachment_context:
            context = (
                f"{context}\n\n{attachment_context}" if context else attachment_context
            )
        system_msg = self._system_prompt(context)
        prompt = [
            {"role": "system", "content": system_msg},
            *self._history_from_messages(history),
        ]

        async for token in self._stream_completion(
            prompt,
            session_id,
            session.workspace_id,
            db,
            user_id,
            disabled_mcp_tools,
            session.model,
            parent_message_id=last_assistant.parent_id,
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
        """Edit a user message as a new conversation branch."""
        session = await self.get_session(session_id, user_id, db)
        active = self._active_messages(session)
        target_index = next(
            (
                index
                for index, message in enumerate(active)
                if message.id == message_id and message.role == "user"
            ),
            None,
        )
        if target_index is None:
            raise ChatValidationError("User message not found")

        target = active[target_index]
        new_user = ChatMessage(
            session_id=session_id,
            role="user",
            content=new_content.strip(),
            attachment_ids=target.attachment_ids,
            parent_id=target.parent_id,
            created_at=_utcnow(),
        )
        db.add(new_user)
        session.updated_at = datetime.now(UTC).replace(tzinfo=None)
        await db.commit()

        context, _sources = (
            await self.build_context(new_content, session.workspace_id, db)
            if session.workspace_id
            else ("", [])
        )
        attachment_context = await self.attachment_context(
            self._attachment_ids(new_user), user_id, db
        )
        if attachment_context:
            context = (
                f"{context}\n\n{attachment_context}" if context else attachment_context
            )
        prompt = [
            {"role": "system", "content": self._system_prompt(context)},
            *self._history_from_messages(active[:target_index]),
            {"role": "user", "content": new_content.strip()},
        ]

        async for token in self._stream_completion(
            prompt,
            session_id,
            session.workspace_id,
            db,
            user_id,
            disabled_mcp_tools,
            session.model,
            parent_message_id=new_user.id,
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
        model: str | None,
        *,
        parent_message_id: uuid.UUID | None = None,
    ) -> AsyncGenerator[str]:
        provider = self._provider if self._custom_provider else get_provider(model)
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

            async for event in provider.stream(messages, schemas):
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
            session_id=session_id,
            role="assistant",
            content=full_response,
            parent_id=parent_message_id,
            created_at=_utcnow(),
        )
        db.add(assistant_msg)
        await db.flush()
        session = await db.get(ChatSession, session_id)
        if session is not None:
            session.active_leaf_id = assistant_msg.id
            session.updated_at = _utcnow()
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
        self, session_id: UUID, user_id: UUID | None, db: AsyncSession
    ) -> ChatSession:
        """Load an owned session with messages."""
        result = await db.execute(
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(ChatSession.id == session_id)
            .execution_options(populate_existing=True)
        )
        session = result.scalar_one_or_none()
        if session is not None:
            messages = (
                (
                    await db.execute(
                        select(ChatMessage)
                        .where(ChatMessage.session_id == session_id)
                        .order_by(ChatMessage.created_at, ChatMessage.id)
                    )
                )
                .scalars()
                .all()
            )
            session.messages = list(messages)
        if session is None or (user_id is not None and session.user_id != user_id):
            raise ChatSessionNotFoundError("Chat session not found")
        return session

    async def rename_session(
        self,
        session_id: UUID,
        user_id: UUID,
        db: AsyncSession,
        *,
        title: str | None = None,
        model: str | None = None,
    ) -> ChatSession:
        """Rename an owned session and/or change its model."""
        session = await self.get_session(session_id, user_id, db)
        if title is not None:
            session.title = title.strip()
        if model is not None:
            session.model = model
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


# Singleton instance
chat_service = ChatService()
