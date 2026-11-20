# Runtime (optional IDE + terminal)

The optional `runtime` compose profile provides a browser IDE (code-server) and browser
terminal (ttyd). It is disabled by default and is never required by the core app.

## Start

```bash
docker compose --profile runtime up -d
# if you changed runtime build args, rebuild first:
docker compose --profile runtime build runtime-ide runtime-terminal
```

This starts:

- `runtime-ide` — code-server on the shared workspace volume (admin only)
- `runtime-terminal` — ttyd on the same workspace volume, mounted read-only (member+)
- `caddy` — edge proxy on http://localhost:8090
- `runtime-init` — one-shot volume ownership bootstrap for the non-root coder user

## URLs

| Service | Local URL |
| --- | --- |
| App | `http://localhost:8090` |
| IDE | `http://localhost:8091` |
| Terminal | `http://localhost:8092` |

Locally, routes use dedicated ports so the session cookie set for `localhost` is sent to
the runtime services. In production, hostnames (for example `app.example.com`,
`ide.example.com`, and `terminal.example.com`) can be used with TLS and a shared cookie
domain.

## Enabling in the UI

1. Sign in as an admin.
2. Settings → enable `features.code_server` and/or `features.terminal`.
3. The sidebar shows **IDE** (admin only) and **Terminal** entries when enabled.

## Access model

- IDE: admin only.
- Terminal: member and above.
- Caddy calls `GET /api/auth/verify?role=admin|member` with the browser session cookie
  before proxying; FastAPI enforces the role.
- The API never exposes runtime ports; Caddy is the only edge.

## Workspace

Both services mount the same `api_uploads` volume used by documents:

- IDE: `/home/coder/workspace` (read-write)
- Terminal: `/home/coder/workspace` (read-only)

This is one shared workspace for v1, as agreed. Users can browse and edit uploaded
documents and conversion artifacts.

## Security model

- Off by default (`features.*` flags and compose profile).
- Runs as a non-root `coder` user (uid 1000); `runtime-init` grants volume ownership.
- No Docker socket and no host process execution beyond the container shell.
- `no-new-privileges`, dropped capabilities, tmpfs `/tmp`, CPU/memory limits.
- Forward-auth on every request; no direct host ports for runtime services.
- The terminal mount is read-only by default; members cannot mutate workspace files.
- AuditIDE/terminal **session-level auditing is not yet implemented**; do not expose this
  profile on the public internet until it is.

## Optional runtimes

Build args control optional language runtimes:

```bash
docker compose --profile runtime build \
  --build-arg INSTALL_NODE=true \
  --build-arg INSTALL_PYTHON=true \
  runtime-ide runtime-terminal
```

Defaults are `false`. Set `RUNTIME_INSTALL_NODE=true` / `RUNTIME_INSTALL_PYTHON=true` in
`.env` to enable them for normal profile builds.

## Environment

| Variable | Purpose |
| --- | --- |
| `SESSION_COOKIE_DOMAIN` | Shared cookie domain in production (e.g. `.example.com`) |
| `NEXT_PUBLIC_IDE_URL` | IDE URL shown/embedded by the web UI |
| `NEXT_PUBLIC_TERMINAL_URL` | Terminal URL shown/embedded by the web UI |
| `RUNTIME_INSTALL_NODE` | Install Node in the runtime image |
| `RUNTIME_INSTALL_PYTHON` | Install Python in the runtime image |
| `CODE_SERVER_VERSION` | Pinned code-server release |
| `TTYD_VERSION` | Pinned ttyd release |

## Troubleshooting

- **401/403 from Caddy:** sign in again; the session cookie must be valid for the shared
  cookie domain.
- **Blank iframe:** check `features.*` flags and that the runtime profile is running.
- **Cannot write in IDE:** run `docker compose --profile runtime up runtime-init` to
  re-apply volume ownership.
- **Terminal exits:** the ttyd process is the container command; inspect
  `docker compose logs runtime-terminal`.
