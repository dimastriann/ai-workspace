"""
AI Workspace API — Chat Router

Endpoints for streaming conversational AI interactions.
"""

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.errors import ChatSessionNotFoundError
from app.dependencies import require_member, require_same_origin
from app.models.chat import (
    ChatMessageItem,
    ChatMessageRequest,
    ChatSessionDetail,
    ChatSessionRename,
    ChatSessionSummary,
)
from app.models.database import ChatSession, User
from app.services.chat_service import chat_service

router = APIRouter()


def _session_summary(session: ChatSession, message_count: int) -> ChatSessionSummary:
    return ChatSessionSummary(
        id=str(session.id),
        title=session.title,
        workspace_id=str(session.workspace_id) if session.workspace_id else None,
        message_count=message_count,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def _session_detail(session: ChatSession) -> ChatSessionDetail:
    summary = _session_summary(session, len(session.messages))
    return ChatSessionDetail(
        **summary.model_dump(),
        messages=[
            ChatMessageItem(
                id=str(message.id),
                role=message.role,
                content=message.content,
                created_at=message.created_at,
            )
            for message in session.messages
        ],
    )


@router.get("/sessions", response_model=list[ChatSessionSummary])
async def list_sessions(
    workspace_id: UUID | None = Query(None),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
) -> list[ChatSessionSummary]:
    """List the current user's chat sessions."""
    rows = await chat_service.list_sessions(workspace_id, user.id, db)
    return [_session_summary(session, count) for session, count in rows]


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
) -> ChatSessionDetail:
    """Return an owned session with messages."""
    try:
        session = await chat_service.get_session(session_id, user.id, db)
    except ChatSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return _session_detail(session)


@router.patch("/sessions/{session_id}", response_model=ChatSessionSummary)
async def rename_session(
    session_id: UUID,
    data: ChatSessionRename,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
    _: None = Depends(require_same_origin),
) -> ChatSessionSummary:
    """Rename an owned session."""
    try:
        session = await chat_service.rename_session(session_id, data.title, user.id, db)
    except ChatSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return _session_summary(session, len(session.messages))


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
    _: None = Depends(require_same_origin),
):
    """Delete an owned session and its messages."""
    try:
        await chat_service.delete_session(session_id, user.id, db)
    except ChatSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/stream")
async def chat_stream(
    request: ChatMessageRequest,
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_member),
):
    """
    Streaming chat endpoint.
    Returns a text/event-stream of AI-generated tokens.
    """
    # 1. Resolve Session
    session_id_uuid = UUID(request.session_id) if request.session_id else None
    workspace_id_uuid = UUID(request.workspace_id) if request.workspace_id else None

    session = await chat_service.get_or_create_session(
        session_id_uuid, workspace_id_uuid, db, user_id=_user.id
    )

    context = ""
    sources: list[dict[str, object]] = []
    if workspace_id_uuid:
        context, sources = await chat_service.build_context(
            request.message, workspace_id_uuid, db
        )

    # 2. Return SSE Stream
    async def event_generator():
        # Start message with metadata
        yield (
            "data: "
            + json.dumps({"session_id": str(session.id), "event": "start"})
            + "\n\n"
        )
        yield "data: " + json.dumps({"event": "sources", "sources": sources}) + "\n\n"

        async for token in chat_service.chat_stream(
            message=request.message,
            session_id=session.id,
            workspace_id=workspace_id_uuid,
            db=db,
            context=context,
            user_id=_user.id,
            disabled_mcp_tools=request.disabled_mcp_tools,
        ):
            yield "data: " + json.dumps({"token": token}) + "\n\n"

        yield 'data: {"event": "done"}\n\n'

    return StreamingResponse(event_generator(), media_type="text/event-stream")
