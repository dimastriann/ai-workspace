# MCP servers

AI Workspace can expose tools from remote **Model Context Protocol** servers to agents and
workflows. MCP is optional, admin-managed, and disabled by default.

## Enable

1. Sign in as an admin.
2. Open **Settings**.
3. Enable `features.mcp`.
4. Under **MCP servers**, add a server and run **Test** to discover its tools.

## Supported transports

| Transport | Use |
| --- | --- |
| Streamable HTTP | Recommended for hosted MCP endpoints (GitHub, Atlassian, etc.) |
| HTTP + SSE | Legacy MCP endpoints that expose an SSE event stream |

stdio servers are not supported yet. Run them behind a proxy such as `mcp-proxy` or a
gateway that exposes a remote MCP URL, then register that URL here.

## Configuration

- **Name:** unique label used to namespace tools (`mcp__<name>__<tool>`).
- **URL:** absolute HTTP(S) endpoint. HTTPS is required outside development.
- **Headers:** optional JSON object, usually `{"Authorization": "Bearer <token>"}`.
  Values are encrypted at rest and never returned by the API; only header names are shown.
- **Timeout:** per connect/list/call timeout, 1–60 seconds.
- **Enabled:** disabled servers contribute no tools.
- **Tools:** all discovered tools are enabled by default; disable individual tools from the
  **Test** dialog.

## Using MCP in chat

Type `/mcp` in AI Chat to open the MCP panel. It shows configured servers, connection
status, and discovered tools.

- Toggles apply to the **current chat session only**; a new chat resets them.
- **Reconnect** refreshes discovery and is available to members.
- Members can view status and tools; only admins can change global server configuration.
- The panel never exposes auth header values.

## Behaviour

- Tools are namespaced per server to avoid collisions.
- Chat, agent runs, and workflow runs merge built-in tools with enabled MCP tools.
- Discovery is cached briefly; a failing server is skipped and never blocks core features.
- Tool calls are truncated, bounded by the server timeout, and audited.
- Tool output is treated as untrusted text.

## Security notes

- Endpoints and tests are admin-only and same-origin protected.
- URLs are validated; private, loopback, link-local, and reserved addresses are rejected
  outside development.
- Secrets are encrypted with the app secret and masked in API responses and logs.
- No Docker socket or host process execution is involved (remote transport only).

## Troubleshooting

- **Test fails:** check URL, auth headers, server availability, and timeout.
- **No tools in agents:** confirm `features.mcp` is on, the server is enabled, and the
  specific tools are not disabled.
- **Tool name collisions:** names include the server name; rename the server if needed.
