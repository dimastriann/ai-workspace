"""Remote MCP server configuration, discovery, and tool execution."""

import asyncio
import ipaddress
import json
import re
import socket
import time
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from mcp import ClientSession, types
from mcp.client.sse import sse_client
from mcp.client.stdio import (
    StdioServerParameters,
    get_default_environment,
    stdio_client,
)
from mcp.client.streamable_http import (
    create_mcp_http_client,
    streamable_http_client,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.core.errors import (
    McpServerNotFoundError,
    McpValidationError,
)
from app.core.security import decrypt_secret, encrypt_secret
from app.models.database import McpServer
from app.models.mcp import (
    McpServerCreate,
    McpServerUpdate,
    McpTestResponse,
    McpToolInfo,
    McpTransport,
)
from app.services.settings_service import settings_service
from app.services.tools import ToolSpec

CACHE_TTL_SECONDS = 60
MAX_TOOL_OUTPUT = 8000

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


@dataclass(frozen=True)
class McpConfig:
    """Decrypted runtime view of an MCP server row."""

    id: uuid.UUID
    name: str
    transport: str
    url: str
    command: list[str] | None
    env: dict[str, str]
    headers: dict[str, str]
    timeout_seconds: int
    disabled_tools: set[str]


def _tool_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_")
    return slug or "server"


class McpService:
    """Manage MCP servers and expose their tools to agents."""

    def __init__(self) -> None:
        self._cache: dict[uuid.UUID, tuple[float, list[McpToolInfo]]] = {}

    async def list_servers(self, db: AsyncSession) -> list[McpServer]:
        result = await db.execute(select(McpServer).order_by(McpServer.name))
        return list(result.scalars().all())

    async def get_server(self, server_id: uuid.UUID, db: AsyncSession) -> McpServer:
        server = await db.get(McpServer, server_id)
        if server is None:
            raise McpServerNotFoundError("MCP server not found")
        return server

    async def create_server(
        self, data: McpServerCreate, user_id: uuid.UUID, db: AsyncSession
    ) -> McpServer:
        name = " ".join(data.name.split())
        if not name:
            raise McpValidationError("Server name is required")
        await self._validate_target(db, data.transport, data.url, data.command)
        if await self._name_exists(name, db):
            raise McpValidationError("An MCP server with this name already exists")

        is_stdio = data.transport == McpTransport.STDIO
        server = McpServer(
            name=name,
            transport=data.transport.value,
            url="" if is_stdio else data.url,
            command=self._encode_command(data.command) if is_stdio else None,
            env_encrypted=self._encrypt_env(data.env),
            headers_encrypted=self._encrypt_headers(data.headers),
            enabled=data.enabled,
            timeout_seconds=data.timeout_seconds,
            disabled_tools=json.dumps(sorted(set(data.disabled_tools))),
            created_by=user_id,
        )
        db.add(server)
        await db.commit()
        await db.refresh(server)
        return server

    async def update_server(
        self,
        server_id: uuid.UUID,
        data: McpServerUpdate,
        db: AsyncSession,
    ) -> McpServer:
        server = await self.get_server(server_id, db)
        fields = data.model_fields_set

        if "name" in fields and data.name is not None:
            name = " ".join(data.name.split())
            if not name:
                raise McpValidationError("Server name is required")
            if await self._name_exists(name, db, exclude_id=server.id):
                raise McpValidationError("An MCP server with this name already exists")
            server.name = name

        if data.transport is not None:
            server.transport = data.transport.value
        if "url" in fields and data.url is not None:
            server.url = data.url
        if "command" in fields:
            server.command = self._encode_command(data.command)
        if "env" in fields:
            server.env_encrypted = self._encrypt_env(data.env)
        if "headers" in fields:
            server.headers_encrypted = self._encrypt_headers(data.headers)
        if data.enabled is not None:
            server.enabled = data.enabled
        if data.timeout_seconds is not None:
            server.timeout_seconds = data.timeout_seconds
        if data.disabled_tools is not None:
            server.disabled_tools = json.dumps(sorted(set(data.disabled_tools)))

        await self._validate_target(
            db,
            McpTransport(server.transport),
            server.url,
            self._decode_command(server.command) if server.command else None,
        )

        await db.commit()
        await db.refresh(server)
        self._cache.pop(server.id, None)
        return server

    async def delete_server(self, server_id: uuid.UUID, db: AsyncSession) -> McpServer:
        server = await self.get_server(server_id, db)
        await db.delete(server)
        await db.commit()
        self._cache.pop(server.id, None)
        return server

    async def test_server(
        self, server_id: uuid.UUID, db: AsyncSession
    ) -> McpTestResponse:
        server = await self.get_server(server_id, db)
        if server.transport == McpTransport.STDIO.value and not (
            await settings_service.get("features.mcp_stdio", db)
        ):
            return McpTestResponse(
                ok=False,
                error="stdio transport is disabled; enable features.mcp_stdio",
            )
        config = self._config(server)
        try:
            tools = await self.discover(config)
        except Exception as exc:
            server.last_status = "error"
            server.last_error = str(exc)[:2000]
            server.last_checked_at = _utcnow()
            await db.commit()
            return McpTestResponse(ok=False, error=str(exc))

        server.last_status = "ok"
        server.last_error = None
        server.last_checked_at = _utcnow()
        await db.commit()
        self._cache[server.id] = (time.monotonic(), tools)
        return McpTestResponse(ok=True, tools=tools)

    async def discover(self, config: McpConfig) -> list[McpToolInfo]:
        """Connect to a server and list its tools."""
        async with asyncio.timeout(config.timeout_seconds):
            async with self._session(config) as session:
                result = await session.list_tools()
        return [
            McpToolInfo(
                name=tool.name,
                description=tool.description or "",
                input_schema=tool.input_schema or {},
            )
            for tool in result.tools
        ]

    async def call_tool(
        self, config: McpConfig, tool_name: str, arguments: dict[str, Any]
    ) -> str:
        """Call a discovered MCP tool and flatten its content to text."""
        async with asyncio.timeout(config.timeout_seconds):
            async with self._session(config) as session:
                result = await session.call_tool(tool_name, arguments)

        parts: list[str] = []
        for item in getattr(result, "content", []):
            if isinstance(item, types.TextContent):
                parts.append(item.text)
            else:
                parts.append(json.dumps(item.model_dump(), default=str))

        structured = getattr(result, "structured_content", None)
        if structured is not None and not parts:
            parts.append(json.dumps(structured, default=str, ensure_ascii=False))

        output = "\n".join(parts).strip() or "(no output)"
        if getattr(result, "is_error", False):
            output = f"MCP tool error: {output}"
        return output[:MAX_TOOL_OUTPUT]

    def cached_tools(self, server: McpServer) -> list[McpToolInfo]:
        """Return cached discovered tools without making a network call."""
        cached = self._cache.get(server.id)
        return list(cached[1]) if cached else []

    @staticmethod
    def tool_name(server_name: str, tool_name: str) -> str:
        """Return the namespaced tool name used by agents."""
        return f"mcp__{_tool_slug(server_name)}__{_tool_slug(tool_name)}"

    async def list_tool_specs(self, db: AsyncSession) -> list[ToolSpec]:
        """Return enabled MCP tools when the feature flag is on."""
        if not await settings_service.get("features.mcp", db):
            return []

        result = await db.execute(
            select(McpServer)
            .where(McpServer.enabled.is_(True))
            .order_by(McpServer.name)
        )
        servers = list(result.scalars().all())
        stdio_enabled = await settings_service.get("features.mcp_stdio", db)
        specs: list[ToolSpec] = []

        for server in servers:
            if server.transport == McpTransport.STDIO.value and not stdio_enabled:
                continue
            config = self._config(server)
            try:
                tools = await self._cached_tools(config)
            except Exception:
                continue

            for tool in tools:
                if tool.name in config.disabled_tools:
                    continue
                name = self.tool_name(server.name, tool.name)
                specs.append(
                    ToolSpec(
                        name=name,
                        description=f"[{server.name}] {tool.description}".strip(),
                        parameters=tool.input_schema or {"type": "object"},
                        permission="mcp",
                        handler=self._handler(config, tool.name),
                        requires_approval=False,
                    )
                )
        return specs

    async def _cached_tools(self, config: McpConfig) -> list[McpToolInfo]:
        cached = self._cache.get(config.id)
        if cached and time.monotonic() - cached[0] < CACHE_TTL_SECONDS:
            return cached[1]
        tools = await self.discover(config)
        self._cache[config.id] = (time.monotonic(), tools)
        return tools

    @staticmethod
    def _handler(config: McpConfig, tool_name: str):
        async def handler(
            _db: AsyncSession,
            _workspace_id: uuid.UUID,
            arguments: dict[str, Any],
        ) -> str:
            return await mcp_service.call_tool(config, tool_name, arguments)

        return handler

    @staticmethod
    def _config(server: McpServer) -> McpConfig:
        headers: dict[str, str] = {}
        if server.headers_encrypted:
            try:
                headers = json.loads(
                    decrypt_secret(
                        server.headers_encrypted, app_settings.app_secret_key
                    )
                )
            except (ValueError, json.JSONDecodeError):
                headers = {}
        env: dict[str, str] = {}
        if server.env_encrypted:
            try:
                env = json.loads(
                    decrypt_secret(server.env_encrypted, app_settings.app_secret_key)
                )
            except (ValueError, json.JSONDecodeError):
                env = {}
        return McpConfig(
            id=server.id,
            name=server.name,
            transport=server.transport,
            url=server.url,
            command=McpService._decode_command(server.command),
            env={str(key): str(value) for key, value in env.items()},
            headers={str(key): str(value) for key, value in headers.items()},
            timeout_seconds=server.timeout_seconds,
            disabled_tools=set(json.loads(server.disabled_tools or "[]")),
        )

    @staticmethod
    def command_argv(server: McpServer) -> list[str] | None:
        """Return the stdio command argv for a server, if applicable."""
        if server.transport != McpTransport.STDIO.value:
            return None
        return McpService._decode_command(server.command)

    @staticmethod
    def env_names(server: McpServer) -> list[str]:
        """Return the configured environment variable names, values masked."""
        return sorted(McpService._config(server).env)

    @staticmethod
    def header_names(server: McpServer) -> list[str]:
        config = McpService._config(server)
        return sorted(config.headers)

    @staticmethod
    def _encode_command(command: list[str] | None) -> str | None:
        if not command:
            return None
        return json.dumps(list(command))

    @staticmethod
    def _decode_command(raw: str | None) -> list[str] | None:
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, list):
            return None
        return [str(item) for item in parsed]

    @staticmethod
    def _validate_command(command: list[str] | None) -> None:
        if not command or not command[0]:
            raise McpValidationError("stdio servers require a command")
        if len(command) > 20:
            raise McpValidationError("stdio command may have at most 20 arguments")
        for arg in command:
            if not arg or "\x00" in arg or len(arg) > 1000:
                raise McpValidationError("stdio command arguments are invalid")

    @staticmethod
    def _encrypt_env(env: dict[str, str] | None) -> str | None:
        if not env:
            return None
        payload = json.dumps({str(key): str(value) for key, value in env.items()})
        return encrypt_secret(payload, app_settings.app_secret_key)

    @staticmethod
    def _encrypt_headers(headers: dict[str, str] | None) -> str | None:
        if not headers:
            return None
        payload = json.dumps({str(key): str(value) for key, value in headers.items()})
        return encrypt_secret(payload, app_settings.app_secret_key)

    async def _name_exists(
        self,
        name: str,
        db: AsyncSession,
        *,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        statement = select(McpServer.id).where(McpServer.name == name)
        if exclude_id is not None:
            statement = statement.where(McpServer.id != exclude_id)
        return (await db.execute(statement)).first() is not None

    @staticmethod
    async def _validate_target(
        db: AsyncSession,
        transport: McpTransport,
        url: str,
        command: list[str] | None,
    ) -> None:
        """Validate the connection target for the configured transport."""
        if transport == McpTransport.STDIO:
            if not await settings_service.get("features.mcp_stdio", db):
                raise McpValidationError(
                    "stdio transport is disabled; enable features.mcp_stdio"
                )
            McpService._validate_command(command)
        else:
            await McpService._validate_url(url, transport)

    @staticmethod
    async def _validate_url(url: str, transport: McpTransport) -> None:
        del transport
        parsed = urlparse(url)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname:
            raise McpValidationError("MCP URL must be an absolute HTTP(S) URL")
        if parsed.username or parsed.password:
            raise McpValidationError("MCP URL must not contain credentials")
        if parsed.scheme == "http":
            if (
                app_settings.app_env != "development"
                or parsed.hostname not in _LOCAL_HOSTS
            ):
                raise McpValidationError("MCP URLs must use HTTPS")

        addresses = await asyncio.to_thread(
            socket.getaddrinfo, parsed.hostname, parsed.port or 443
        )
        for address in addresses:
            ip = ipaddress.ip_address(address[4][0])
            if ip.is_loopback:
                if app_settings.app_env == "development":
                    continue
                raise McpValidationError("Local MCP URLs are not allowed")
            if ip.is_private or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                raise McpValidationError("MCP URL resolves to a private address")

    @staticmethod
    def _session(config: McpConfig):
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def open_session():
            if config.transport == McpTransport.STDIO.value:
                if not config.command:
                    raise McpValidationError("stdio server has no command")
                params = StdioServerParameters(
                    command=config.command[0],
                    args=config.command[1:],
                    env={**get_default_environment(), **config.env},
                )
                async with stdio_client(params) as (read_stream, write_stream):
                    async with ClientSession(
                        read_stream,
                        write_stream,
                        read_timeout_seconds=config.timeout_seconds,
                    ) as session:
                        await session.initialize()
                        yield session
            elif config.transport == McpTransport.SSE.value:
                async with sse_client(
                    config.url,
                    headers=config.headers,
                    timeout=config.timeout_seconds,
                    sse_read_timeout=config.timeout_seconds,
                ) as (read_stream, write_stream):
                    async with ClientSession(
                        read_stream,
                        write_stream,
                        read_timeout_seconds=config.timeout_seconds,
                    ) as session:
                        await session.initialize()
                        yield session
            else:
                async with create_mcp_http_client(
                    headers=config.headers
                ) as http_client:
                    async with streamable_http_client(
                        config.url, http_client=http_client
                    ) as (read_stream, write_stream):
                        async with ClientSession(
                            read_stream,
                            write_stream,
                            read_timeout_seconds=config.timeout_seconds,
                        ) as session:
                            await session.initialize()
                            yield session

        return open_session()


def _utcnow():
    from datetime import UTC, datetime

    return datetime.now(UTC).replace(tzinfo=None)


mcp_service = McpService()
