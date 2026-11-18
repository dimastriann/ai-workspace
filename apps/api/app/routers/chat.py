"""
AI Workspace API — Chat Router

Endpoints for streaming conversational AI interactions.
"""

import json
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.errors import (
    ChatSessionNotFoundError,
    ChatValidationError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from app.dependencies import require_member, require_same_origin
from app.models.chat import (
    ChatAlternativeRequest,
    ChatAttachmentResponse,
    ChatEditRequest,
    ChatMessageItem,
    ChatMessageRequest,
    ChatModelsResponse,
    ChatRegenerateRequest,
    ChatSessionDetail,
    ChatSessionRename,
    ChatSessionSummary,
)
from app.models.database import ChatMessage, ChatSession, User
from app.services.chat_service import chat_service
from app.services.settings_service import settings_service

router = APIRouter()


def _session_summary(session: ChatSession, message_count: int) -> ChatSessionSummary:
    return ChatSessionSummary(
        id=str(session.id),
        title=session.title,
        workspace_id=str(session.workspace_id) if session.workspace_id else None,
        message_count=message_count,
        model=session.model,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


def _alternatives(message: ChatMessage) -> list[str]:
    try:
        parsed = json.loads(message.alternatives or "[]")
        return [str(item) for item in parsed] if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def _session_detail(session: ChatSession) -> ChatSessionDetail:
    summary = _session_summary(session, len(session.messages))
    return ChatSessionDetail(
        **summary.model_dump(),
        messages=[
            ChatMessageItem(
                id=str(message.id),
                role=message.role,
                content=message.content,
                alternative_count=max(1, len(_alternatives(message))),
                alternative_index=message.active_alternative,
                created_at=message.created_at,
            )
            for message in session.messages
        ],
    )


@router.get("/models", response_model=ChatModelsResponse)
async def list_models(
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_member),
) -> ChatModelsResponse:
    """Return chat models configured by the admin."""
    raw = str(await settings_service.get("llm.available_models", db))
    default = str(await settings_service.get("llm.openai_model", db))
    models = [item.strip() for item in raw.split(",") if item.strip()]
    if default and default not in models:
        models.insert(0, default)
    return ChatModelsResponse(models=models, default=default or None)


@router.get("/sessions", response_model=list[ChatSessionSummary])
async def list_sessions(
    workspace_id: UUID | None = Query(None),
    q: str | None = Query(None, max_length=200),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
) -> list[ChatSessionSummary]:
    """List the current user's chat sessions."""
    rows = await chat_service.list_sessions(workspace_id, user.id, db, q)
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
    """Rename an owned session or change its model."""
    if data.title is None and data.model is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No changes supplied",
        )
    try:
        session = await chat_service.rename_session(
            session_id,
            user.id,
            db,
            title=data.title,
            model=data.model,
        )
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


@router.post("/regenerate")
async def regenerate(
    body: ChatRegenerateRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
    _: None = Depends(require_same_origin),
):
    """Regenerate the latest assistant response."""
    session_id = UUID(body.session_id)
    try:
        session = await chat_service.get_session(session_id, user.id, db)
    except ChatSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    if not session.messages or session.messages[-1].role != "assistant":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nothing to regenerate",
        )

    async def event_generator():
        yield (
            "data: "
            + json.dumps({"session_id": str(session.id), "event": "start"})
            + "\n\n"
        )
        yield 'data: {"event": "sources", "sources": []}\n\n'
        try:
            async for token in chat_service.regenerate_stream(
                session.id,
                db,
                user.id,
                body.disabled_mcp_tools,
            ):
                yield "data: " + json.dumps({"token": token}) + "\n\n"
        except ChatValidationError as exc:
            yield (
                "data: " + json.dumps({"event": "error", "message": str(exc)}) + "\n\n"
            )
            return
        yield 'data: {"event": "done"}\n\n'

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "cache-control": "no-cache, no-transform",
            "x-accel-buffering": "no",
        },
    )


@router.post("/messages/{message_id}/edit")
async def edit_message(
    message_id: UUID,
    body: ChatEditRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
    _: None = Depends(require_same_origin),
):
    """Edit a user message and regenerate the conversation from it."""
    session_id = UUID(body.session_id)
    try:
        session = await chat_service.get_session(session_id, user.id, db)
    except ChatSessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    target = next(
        (
            message
            for message in session.messages
            if message.id == message_id and message.role == "user"
        ),
        None,
    )
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User message not found",
        )

    async def event_generator():
        yield (
            "data: "
            + json.dumps({"session_id": str(session.id), "event": "start"})
            + "\n\n"
        )
        yield 'data: {"event": "sources", "sources": []}\n\n'
        try:
            async for token in chat_service.edit_message_stream(
                session.id,
                message_id,
                body.message,
                db,
                user.id,
                body.disabled_mcp_tools,
            ):
                yield "data: " + json.dumps({"token": token}) + "\n\n"
        except ChatValidationError as exc:
            yield (
                "data: " + json.dumps({"event": "error", "message": str(exc)}) + "\n\n"
            )
            return
        yield 'data: {"event": "done"}\n\n'

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "cache-control": "no-cache, no-transform",
            "x-accel-buffering": "no",
        },
    )


@router.post("/attachments", response_model=ChatAttachmentResponse)
async def upload_attachment(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
) -> ChatAttachmentResponse:
    """Extract and store a file attachment for chat."""
    data = await file.read()
    try:
        attachment = await chat_service.create_attachment(
            file.filename or "attachment", data, user.id, db
        )
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        ) from exc
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc)
        ) from exc
    return ChatAttachmentResponse(
        id=str(attachment.id),
        filename=attachment.filename,
        size_bytes=attachment.size_bytes,
        characters=len(attachment.content_text),
    )


@router.patch("/messages/{message_id}/alternative")
async def choose_alternative(
    message_id: UUID,
    data: ChatAlternativeRequest,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
    _: None = Depends(require_same_origin),
):
    """Select an alternative response for an assistant message."""
    try:
        message = await chat_service.choose_alternative(
            message_id, data.index, user.id, db
        )
    except ChatValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return {
        "id": str(message.id),
        "content": message.content,
        "alternative_index": message.active_alternative,
    }


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
        session_id_uuid,
        workspace_id_uuid,
        db,
        user_id=_user.id,
        model=request.model,
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
            model=request.model,
            attachment_ids=request.attachment_ids,
        ):
            yield "data: " + json.dumps({"token": token}) + "\n\n"

        yield 'data: {"event": "done"}\n\n'

    return StreamingResponse(event_generator(), media_type="text/event-stream")
