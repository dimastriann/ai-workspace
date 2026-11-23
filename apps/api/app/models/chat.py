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
    model: str | None = Field(default=None, max_length=120)
    attachment_ids: list[str] = Field(default_factory=list, max_length=5)


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
    branch_count: int = 1
    branch_index: int = 0
    attachments: list["ChatAttachmentResponse"] = Field(default_factory=list)
    created_at: datetime


class ChatSessionSummary(BaseModel):
    """Chat session metadata for the history sidebar."""

    id: str
    title: str
    workspace_id: str | None = None
    message_count: int = 0
    model: str | None = None
    created_at: datetime
    updated_at: datetime


class ChatSessionDetail(ChatSessionSummary):
    """A session with its persisted messages."""

    messages: list[ChatMessageItem] = Field(default_factory=list)


class ChatSessionRename(BaseModel):
    """Rename a chat session or change its model."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    model: str | None = Field(default=None, max_length=120)


class ChatRegenerateRequest(BaseModel):
    """Regenerate the latest assistant response."""

    session_id: str
    disabled_mcp_tools: list[str] = Field(default_factory=list, max_length=200)


class ChatEditRequest(BaseModel):
    """Edit a user message and continue the conversation."""

    session_id: str
    message: str = Field(..., min_length=1, max_length=4000)
    disabled_mcp_tools: list[str] = Field(default_factory=list, max_length=200)
    attachment_ids: list[str] | None = Field(
        default=None,
        max_length=5,
        description="Replacement attachment list; omitted keeps the originals",
    )


class ChatModelsResponse(BaseModel):
    """Models available for chat."""

    models: list[str] = Field(default_factory=list)
    default: str | None = None


class ChatAttachmentResponse(BaseModel):
    """An uploaded chat attachment."""

    id: str
    filename: str
    size_bytes: int
    characters: int
    is_image: bool = False


class ChatBranchRequest(BaseModel):
    """Select a message branch as the active conversation path."""

    index: int = Field(..., ge=0)
