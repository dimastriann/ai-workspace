"""
AI Workspace API — Chat Service

Orchestrates the conversational AI logic:
1. Session management (PostgreSQL history).
2. Lexical context retrieval (Postgres full-text search).
3. Streaming response generation through the shared provider.
"""

from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import ChatMessage, ChatSession
from app.services.agent_provider import AgentProvider, get_provider
from app.services.retrieval import retrieval_service


class ChatService:
    def __init__(self, provider: AgentProvider | None = None):
        self._provider = provider or get_provider()

    async def get_or_create_session(
        self, session_id: UUID | None, workspace_id: UUID | None, db: AsyncSession
    ) -> ChatSession:
        """Fetch an existing session or create a new one."""
        if session_id:
            result = await db.execute(
                select(ChatSession).where(ChatSession.id == session_id)
            )
            session = result.scalar_one_or_none()
            if session:
                return session

        new_session = ChatSession(
            id=session_id or uuid4(),
            workspace_id=workspace_id,
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
        await db.commit()

        full_response = ""
        async for event in self._provider.stream(messages, []):
            if event.type == "token":
                full_response += event.content
                yield event.content

        assistant_msg = ChatMessage(
            session_id=session_id, role="assistant", content=full_response
        )
        db.add(assistant_msg)
        await db.commit()

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
