"""
AI Workspace API — Chat Router

Endpoints for streaming conversational AI interactions.
"""

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.chat_service import chat_service
from app.models.chat import ChatMessageRequest


router = APIRouter()


@router.post("/stream")
async def chat_stream(
    request: ChatMessageRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Streaming chat endpoint.
    Returns a text/event-stream of AI-generated tokens.
    """
    # 1. Resolve Session
    session_id_uuid = UUID(request.session_id) if request.session_id else None
    workspace_id_uuid = UUID(request.workspace_id) if request.workspace_id else None
    
    session = await chat_service.get_or_create_session(
        session_id_uuid, 
        workspace_id_uuid, 
        db
    )

    # 2. Return SSE Stream
    async def event_generator():
        # Start message with metadata
        yield f"data: {{\"session_id\": \"{session.id}\", \"event\": \"start\"}}\n\n"
        
        async for token in chat_service.chat_stream(
            message=request.message,
            session_id=session.id,
            workspace_id=workspace_id_uuid,
            db=db
        ):
            yield f"data: {{\"token\": {json.dumps(token)}}}\n\n"
            
        yield "data: {\"event\": \"done\"}\n\n"

    import json
    return StreamingResponse(event_generator(), media_type="text/event-stream")
