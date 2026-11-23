"""MCP server configuration and discovery models."""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class McpTransport(StrEnum):
    """Supported MCP transports."""

    HTTP = "http"
    SSE = "sse"
    STDIO = "stdio"


class McpServerCreate(BaseModel):
    """Register an MCP server."""

    name: str = Field(..., min_length=1, max_length=120)
    transport: McpTransport = McpTransport.HTTP
    url: str = Field(default="", max_length=1000)
    command: list[str] | None = None
    env: dict[str, str] | None = None
    headers: dict[str, str] | None = None
    enabled: bool = True
    timeout_seconds: int = Field(default=10, ge=1, le=60)
    disabled_tools: list[str] = Field(default_factory=list)


class McpServerUpdate(BaseModel):
    """Update an MCP server; omitted fields are unchanged."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    transport: McpTransport | None = None
    url: str | None = Field(default=None, max_length=1000)
    command: list[str] | None = None
    env: dict[str, str] | None = None
    headers: dict[str, str] | None = None
    enabled: bool | None = None
    timeout_seconds: int | None = Field(default=None, ge=1, le=60)
    disabled_tools: list[str] | None = None


class McpToolInfo(BaseModel):
    """A tool discovered from a remote MCP server."""

    name: str
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)


class McpServerResponse(BaseModel):
    """MCP server metadata with secrets masked."""

    id: str
    name: str
    transport: str
    url: str
    command: list[str] | None = None
    env_names: list[str] = Field(default_factory=list)
    header_names: list[str] = Field(default_factory=list)
    oauth_connected: bool = False
    enabled: bool
    timeout_seconds: int
    disabled_tools: list[str]
    last_status: str | None = None
    last_error: str | None = None
    last_checked_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class McpOAuthStartRequest(BaseModel):
    """Start the OAuth browser flow for a server."""

    redirect_uri: str = Field(..., min_length=1, max_length=1000)


class McpOAuthStartResponse(BaseModel):
    """The authorization URL the browser must open."""

    authorize_url: str


class McpTestResponse(BaseModel):
    """Result of testing a server connection."""

    ok: bool
    tools: list[McpToolInfo] = Field(default_factory=list)
    error: str | None = None


class McpStatusTool(BaseModel):
    """A tool exposed in the chat MCP panel."""

    name: str
    label: str
    description: str = ""
    enabled: bool = True


class McpStatusServer(BaseModel):
    """Server status for the chat MCP panel."""

    id: str
    name: str
    transport: str
    enabled: bool
    status: str | None = None
    error: str | None = None
    last_checked_at: datetime | None = None
    tools: list[McpStatusTool] = Field(default_factory=list)


class McpStatusResponse(BaseModel):
    """MCP availability for the current chat session."""

    feature_enabled: bool
    servers: list[McpStatusServer] = Field(default_factory=list)


class McpToolCallRequest(BaseModel):
    """Arguments for a tool call."""

    arguments: dict[str, Any] = Field(default_factory=dict)


class McpServerIdRequest(BaseModel):
    """Internal helper for typed IDs."""

    server_id: UUID
