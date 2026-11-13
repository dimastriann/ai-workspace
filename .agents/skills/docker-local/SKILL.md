---
name: docker-local
description: Optionally rebuild, migrate, and smoke-test the local Docker stack. Use only when the user asks to deploy locally and Docker is available; skip cleanly when Docker is missing.
license: MIT
compatibility: claude-code,codex,opencode
metadata:
  version: "1.0"
---

# Local Docker deployment (optional)

## Detect first

Check, in order:

- `docker --version`
- `docker info` (use a short timeout)
- `docker compose version`

If any check fails, print `SKIP: Docker not available` and continue without Docker.
Never block other work on Docker.

## If Docker is available

1. Inspect: `docker compose ps`.
2. Build only what changed, for example `docker compose build api worker web`.
3. Apply migrations: `docker compose run --rm api alembic upgrade head`.
4. Start: `docker compose up -d api worker web`.
5. Smoke test: `curl http://localhost:8000/health` and open `http://localhost:3000/login`.

Do not run destructive commands such as `docker compose down -v` without explicit user
confirmation. Do not rebuild images that did not change.

## If Docker is unavailable

Use local processes instead:

- API: `uv run uvicorn app.main:app --reload` from `apps/api`
- Web: `pnpm --filter web dev`
- PostgreSQL is still required.

Mention the Docker issue once and continue.
