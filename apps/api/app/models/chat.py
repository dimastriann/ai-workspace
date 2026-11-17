"""
AI Workspace API — Chat Models

Pydantic schemas for chat message requests and responses.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ChatMessageRequest(BaseModel):
    """Request body for sending a chat message."""

    message: str = Field(..., min_length=1, description="The user's message")
    session_id: str | None = Field(
        None, description="Chat session ID (auto-created if not provided)"
    )
    workspace_id: str | None = Field(
        None, description="Workspace context for the conversation"
    )
    disabled_mcp_tools: list[str] = Field(
        default_factory=list,
        max_length=200,
        description="Namespaced MCP tools disabled for this chat message",
    )


class ChatMessageResponse(BaseModel):
    """Response from the AI chat."""

    session_id: str
    message: str
    role: str = "assistant"
    created_at: datetime = Field(default_factory=datetime.now)


class ChatSession(BaseModel):
    """Chat session metadata."""

    id: str
    title: str
    workspace_id: str | None = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class ChatMessageItem(BaseModel):
    """A persisted chat message."""

    id: str
    role: str
    content: str
    created_at: datetime


class ChatSessionSummary(BaseModel):
    """Chat session metadata for the history sidebar."""

    id: str
    title: str
    workspace_id: str | None = None
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class ChatSessionDetail(ChatSessionSummary):
    """A session with its persisted messages."""

    messages: list[ChatMessageItem] = Field(default_factory=list)


class ChatSessionRename(BaseModel):
    """Rename a chat session."""

    title: str = Field(..., min_length=1, max_length=255)
