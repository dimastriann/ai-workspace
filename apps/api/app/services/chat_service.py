"""
AI Workspace API — Chat Service

Orchestrates the conversational AI logic using LangChain:
1. Session management (PostgreSQL history).
2. RAG context retrieval (Qdrant search).
3. Streaming response generation (OpenAI/Ollama).
"""

import json
from uuid import UUID
from typing import AsyncGenerator, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.database import ChatSession, ChatMessage
from app.core.vector_store import qdrant_client, get_collection_name
from app.services.embedding_service import embedding_service


class ChatService:
    def __init__(self):
        self._llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            streaming=True
        )

    async def get_or_create_session(
        self, 
        session_id: Optional[UUID], 
        workspace_id: Optional[UUID], 
        db: AsyncSession
    ) -> ChatSession:
        """Fetch an existing session or create a new one."""
        if session_id:
            result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
            session = result.scalar_one_or_none()
            if session:
                return session
        
        # Create new session
        new_session = ChatSession(
            id=session_id or uuid.uuid4(),
            workspace_id=workspace_id,
            title="New Conversation"
        )
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        return new_session

    async def chat_stream(
        self, 
        message: str, 
        session_id: UUID, 
        workspace_id: Optional[UUID],
        db: AsyncSession
    ) -> AsyncGenerator[str, None]:
        """
        Main chat loop with RAG and streaming.
        """
        # 1. Retrieve Context (RAG)
        context = ""
        if workspace_id:
            context = await self._get_context(message, workspace_id)

        # 2. Prepare History
        history = await self._get_history(session_id, db)
        
        # 3. Construct Prompt
        system_msg = "You are a helpful AI assistant in the AI Workspace platform."
        if context:
            system_msg += f"\n\nUse the following context from the documents to answer the user if relevant:\n{context}"
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ])

        # 4. Save User Message
        user_msg = ChatMessage(session_id=session_id, role="user", content=message)
        db.add(user_msg)
        await db.commit()

        # 5. Stream from LLM
        full_response = ""
        chain = prompt | self._llm
        
        async for chunk in chain.astream({"input": message, "history": history}):
            content = chunk.content
            full_response += content
            yield content

        # 6. Save Assistant Message
        assistant_msg = ChatMessage(session_id=session_id, role="assistant", content=full_response)
        db.add(assistant_msg)
        await db.commit()

    async def _get_context(self, query: str, workspace_id: UUID) -> str:
        """Perform semantic search in Qdrant."""
        try:
            query_vector = await embedding_service.embed_query(query)
            collection_name = get_collection_name(str(workspace_id))
            
            search_results = qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=5
            )
            
            return "\n---\n".join([r.payload["content"] for r in search_results])
        except Exception:
            return ""

    async def _get_history(self, session_id: UUID, db: AsyncSession) -> List:
        """Load recent message history for the session."""
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(10)
        )
        messages = list(result.scalars().all())
        messages.reverse()
        
        history = []
        for m in messages:
            if m.role == "user":
                history.append(HumanMessage(content=m.content))
            else:
                history.append(AIMessage(content=m.content))
        return history


# Singleton instance
chat_service = ChatService()
