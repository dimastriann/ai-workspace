"""
AI Workspace API — Chat Service

Orchestrates the conversational AI logic:
1. Session management (PostgreSQL history).
2. Lexical context retrieval (Postgres full-text search).
3. Streaming response generation (OpenAI/Ollama).
"""

from collections.abc import AsyncGenerator
from uuid import UUID, uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import ChatMessage, ChatSession
from app.services.retrieval import retrieval_service


class ChatService:
    def __init__(self):
        self._llm = ChatOpenAI(
            api_key=settings.openai_api_key, model=settings.openai_model, streaming=True
        )

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

        # Create new session
        new_session = ChatSession(
            id=session_id or uuid4(),
            workspace_id=workspace_id,
            title="New Conversation",
        )
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        return new_session

    async def chat_stream(
        self,
        message: str,
        session_id: UUID,
        workspace_id: UUID | None,
        db: AsyncSession,
    ) -> AsyncGenerator[str]:
        """
        Main chat loop with RAG and streaming.
        """
        # 1. Retrieve Context (RAG)
        context = ""
        if workspace_id:
            context = await self._get_context(message, workspace_id, db)

        # 2. Prepare History
        history = await self._get_history(session_id, db)

        # 3. Construct Prompt
        system_msg = "You are a helpful AI assistant in the AI Workspace platform."
        if context:
            system_msg += (
                "\n\nUse the following context from the documents to answer "
                f"the user if relevant:\n{context}"
            )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_msg),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{input}"),
            ]
        )

        # 4. Save User Message
        user_msg = ChatMessage(session_id=session_id, role="user", content=message)
        db.add(user_msg)
        await db.commit()

        # 5. Stream from LLM
        full_response = ""
        chain = prompt | self._llm

        async for chunk in chain.astream({"input": message, "history": history}):
            content = chunk.content if isinstance(chunk.content, str) else ""
            full_response += content
            yield content

        # 6. Save Assistant Message
        assistant_msg = ChatMessage(
            session_id=session_id, role="assistant", content=full_response
        )
        db.add(assistant_msg)
        await db.commit()

    async def _get_context(
        self, query: str, workspace_id: UUID, db: AsyncSession
    ) -> str:
        """Retrieve relevant chunks with Postgres full-text search."""
        try:
            chunks = await retrieval_service.search(query, workspace_id, db)
            return "\n---\n".join(chunks)
        except Exception:
            return ""

    async def _get_history(
        self, session_id: UUID, db: AsyncSession
    ) -> list[BaseMessage]:
        """Load recent message history for the session."""
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(10)
        )
        messages = list(result.scalars().all())
        messages.reverse()

        history: list[BaseMessage] = []
        for m in messages:
            if m.role == "user":
                history.append(HumanMessage(content=m.content))
            else:
                history.append(AIMessage(content=m.content))
        return history


# Singleton instance
chat_service = ChatService()
