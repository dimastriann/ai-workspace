"""Admin-only MCP server configuration and discovery endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.errors import McpServerNotFoundError, McpValidationError
from app.dependencies import require_admin, require_member, require_same_origin
from app.models.database import McpServer, User
from app.models.mcp import (
    McpOAuthStartRequest,
    McpOAuthStartResponse,
    McpServerCreate,
    McpServerResponse,
    McpServerUpdate,
    McpStatusResponse,
    McpStatusServer,
    McpStatusTool,
    McpTestResponse,
)
from app.services.audit_service import audit_service
from app.services.mcp_oauth_service import McpOAuthError, mcp_oauth_service
from app.services.mcp_service import mcp_service
from app.services.settings_service import settings_service

router = APIRouter()


def _response(server: McpServer) -> McpServerResponse:
    return McpServerResponse(
        id=str(server.id),
        name=server.name,
        transport=server.transport,
        url=server.url,
        command=mcp_service.command_argv(server),
        env_names=mcp_service.env_names(server),
        header_names=mcp_service.header_names(server),
        oauth_connected=mcp_oauth_service.load_bundle(server) is not None,
        enabled=server.enabled,
        timeout_seconds=server.timeout_seconds,
        disabled_tools=sorted(set(_json_list(server.disabled_tools))),
        last_status=server.last_status,
        last_error=server.last_error,
        last_checked_at=server.last_checked_at,
        created_at=server.created_at,
        updated_at=server.updated_at,
    )


def _json_list(value: str) -> list[str]:
    import json

    try:
        parsed = json.loads(value or "[]")
        return [str(item) for item in parsed] if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


@router.get("/status", response_model=McpStatusResponse)
async def mcp_status(
    db: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_member),
) -> McpStatusResponse:
    """Return MCP availability and cached tools for the chat panel."""
    feature_enabled = bool(await settings_service.get("features.mcp", db))
    servers = await mcp_service.list_servers(db)
    status_servers: list[McpStatusServer] = []

    for server in servers:
        disabled = set(_json_list(server.disabled_tools))
        tools = [
            McpStatusTool(
                name=mcp_service.tool_name(server.name, tool.name),
                label=tool.name,
                description=tool.description,
                enabled=server.enabled and tool.name not in disabled,
            )
            for tool in mcp_service.cached_tools(server)
        ]
        status_servers.append(
            McpStatusServer(
                id=str(server.id),
                name=server.name,
                transport=server.transport,
                enabled=server.enabled,
                status=server.last_status,
                error=server.last_error,
                last_checked_at=server.last_checked_at,
                tools=tools,
            )
        )

    return McpStatusResponse(feature_enabled=feature_enabled, servers=status_servers)


@router.get("/servers", response_model=list[McpServerResponse])
async def list_servers(
    db: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_admin),
) -> list[McpServerResponse]:
    """List configured MCP servers with secrets masked."""
    servers = await mcp_service.list_servers(db)
    return [_response(server) for server in servers]


@router.post("/servers", response_model=McpServerResponse, status_code=201)
async def create_server(
    data: McpServerCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(require_admin),
    _: None = Depends(require_same_origin),
) -> McpServerResponse:
    """Register a remote MCP server."""
    try:
        server = await mcp_service.create_server(data, admin.id, db)
    except McpValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    await audit_service.record(
        db,
        action="mcp.create",
        actor_id=admin.id,
        target=str(server.id),
        details={"name": server.name, "transport": server.transport},
        ip=request.client.host if request.client else None,
    )
    return _response(server)


@router.get("/servers/{server_id}", response_model=McpServerResponse)
async def get_server(
    server_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_admin),
) -> McpServerResponse:
    """Return one MCP server."""
    try:
        server = await mcp_service.get_server(server_id, db)
    except McpServerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return _response(server)


@router.put("/servers/{server_id}", response_model=McpServerResponse)
async def update_server(
    server_id: UUID,
    data: McpServerUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(require_admin),
    _: None = Depends(require_same_origin),
) -> McpServerResponse:
    """Update an MCP server."""
    try:
        server = await mcp_service.update_server(server_id, data, db)
    except McpServerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except McpValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    await audit_service.record(
        db,
        action="mcp.update",
        actor_id=admin.id,
        target=str(server.id),
        details={"name": server.name, "enabled": server.enabled},
        ip=request.client.host if request.client else None,
    )
    return _response(server)


@router.delete("/servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(
    server_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(require_admin),
    _: None = Depends(require_same_origin),
):
    """Delete an MCP server."""
    try:
        server = await mcp_service.delete_server(server_id, db)
    except McpServerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    await audit_service.record(
        db,
        action="mcp.delete",
        actor_id=admin.id,
        target=str(server.id),
        details={"name": server.name},
        ip=request.client.host if request.client else None,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/servers/{server_id}/test", response_model=McpTestResponse)
async def test_server(
    server_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(require_admin),
    _: None = Depends(require_same_origin),
) -> McpTestResponse:
    """Connect to the server and discover its tools."""
    try:
        result = await mcp_service.test_server(server_id, db)
    except McpServerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    await audit_service.record(
        db,
        action="mcp.test",
        actor_id=admin.id,
        target=str(server_id),
        details={"ok": result.ok, "tools": len(result.tools)},
        ip=request.client.host if request.client else None,
    )
    return result


@router.post("/servers/{server_id}/reconnect", response_model=McpTestResponse)
async def reconnect_server(
    server_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(require_member),
    _: None = Depends(require_same_origin),
) -> McpTestResponse:
    """Refresh a server's discovery cache for any member."""
    try:
        result = await mcp_service.test_server(server_id, db)
    except McpServerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    await audit_service.record(
        db,
        action="mcp.reconnect",
        actor_id=user.id,
        target=str(server_id),
        details={"ok": result.ok, "tools": len(result.tools)},
        ip=request.client.host if request.client else None,
    )
    return result


@router.get("/servers/{server_id}/tools", response_model=McpTestResponse)
async def list_tools(
    server_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_admin),
) -> McpTestResponse:
    """Discover tools for a configured server."""
    try:
        return await mcp_service.test_server(server_id, db)
    except McpServerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.post("/servers/{server_id}/oauth/start", response_model=McpOAuthStartResponse)
async def start_oauth(
    server_id: UUID,
    data: McpOAuthStartRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(require_admin),
    _: None = Depends(require_same_origin),
) -> McpOAuthStartResponse:
    """Begin the OAuth browser flow: discover, register, build authorize URL."""
    try:
        server = await mcp_service.get_server(server_id, db)
        if server.transport not in {"http", "sse"}:
            raise McpValidationError("OAuth applies to remote transports only")
        authorize_url = await mcp_oauth_service.start_authorization(
            server, data.redirect_uri
        )
    except McpServerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (McpValidationError, McpOAuthError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    await audit_service.record(
        db,
        action="mcp.oauth_start",
        actor_id=admin.id,
        target=str(server.id),
        details={"name": server.name},
        ip=request.client.host if request.client else None,
    )
    return McpOAuthStartResponse(authorize_url=authorize_url)


@router.get("/oauth/callback", response_class=HTMLResponse)
async def oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    """OAuth redirect target: exchange the code and close the popup."""
    if error:
        return _callback_page(f"Authorization failed: {error}")
    pending = mcp_oauth_service.get_pending(state) if state else None
    if pending is None or not code:
        return _callback_page("Unknown or expired OAuth state.")

    try:
        server = await mcp_service.get_server(UUID(pending.server_id), db)
        await mcp_oauth_service.complete_authorization(server, pending, code)
        await db.commit()
        await audit_service.record(
            db,
            action="mcp.oauth_connect",
            target=str(server.id),
            details={"name": server.name},
        )
    except (McpOAuthError, McpServerNotFoundError) as exc:
        return _callback_page(f"Authorization failed: {exc}")
    return _callback_page(
        f"Connected <strong>{server.name}</strong>. You can close this window."
    )


def _callback_page(message: str) -> HTMLResponse:
    safe = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return HTMLResponse(
        "<!doctype html><meta charset='utf-8'>"
        "<title>AI Workspace MCP</title>"
        f"<p>{safe}</p><script>window.close()</script>"
    )


@router.delete("/servers/{server_id}/oauth", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_oauth(
    server_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    admin: User = Depends(require_admin),
    _: None = Depends(require_same_origin),
):
    """Remove stored OAuth tokens for a server."""
    try:
        server = await mcp_service.get_server(server_id, db)
    except McpServerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    mcp_oauth_service.disconnect(server)
    await db.commit()
    await audit_service.record(
        db,
        action="mcp.oauth_disconnect",
        actor_id=admin.id,
        target=str(server.id),
        details={"name": server.name},
        ip=request.client.host if request.client else None,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
