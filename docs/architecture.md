# Architecture

## Overview

```
Browser
  │  same-origin /api/*
  ▼
apps/web (Next.js 16)  ── BFF route handlers ──►  apps/api (FastAPI)
  │                                                   │
  │                                                   ├─ PostgreSQL (only mandatory service)
  │                                                   ├─ worker (Postgres job queue)
  │                                                   ├─ Qdrant        [optional]
  │                                                   ├─ Redis         [optional]
  │                                                   └─ Rust parser   [optional]
  │
  └─ Caddy ──► runtime container (code-server / terminal)   [optional, Phase 5]
```

## Components

| Component | Responsibility |
|---|---|
| `apps/web` | Next.js UI, session-cookie handling, same-origin BFF, SSE proxying |
| `apps/api` | Auth, RBAC, workspaces, documents, chat, RAG, agents, settings |
| `worker` | Claims `jobs` with `FOR UPDATE SKIP LOCKED`; ingestion and future conversion |
| `postgres` | Source of truth: users, sessions, documents, chunks, jobs, runs, settings, audit |
| `qdrant` | Optional semantic retrieval; default retrieval is Postgres FTS |
| `redis` | Optional cache/rate-limit acceleration; not required |
| `rust/parser` | Optional parsing accelerator; Python parsing is the fallback |

## Data flows

### Auth
1. Browser posts credentials to `/api/auth/login` on the BFF.
2. BFF forwards to FastAPI; FastAPI verifies argon2 and creates a hashed opaque session.
3. FastAPI sets an `httpOnly`, `SameSite=Lax` cookie; the BFF preserves it.
4. Subsequent requests carry the cookie through the BFF; FastAPI resolves the user and role.

### Upload and ingestion
1. Upload goes through the BFF; FastAPI validates type and size.
2. FastAPI stores the file under `uploads/{workspace_id}/` and creates a `jobs` row.
3. The worker claims the job, parses the document locally, chunks it, and stores chunks.
4. No AI or vector database is required for this path.

### Chat and retrieval
1. Chat resolves or creates a session.
2. Retrieval runs Postgres full-text search over `document_chunks` for the workspace.
3. Sources are streamed first, then LLM tokens.
4. Messages are persisted after the response completes.

### Agents
1. A run is created and streamed over SSE.
2. The executor exposes only tools permitted by the selected skill.
3. Tool calls are persisted as `agent_steps`; the result is stored on the run.

## Storage

- `uploads/` — original documents (Docker volume `api_uploads`).
- `document_chunks` — lexical retrieval index.
- `jobs` — durable queue.
- `agent_runs` / `agent_steps` — execution history.
- `app_settings` — runtime configuration, secrets encrypted with Fernet.
- `audit_log` — logins, admin changes, and future security events.

## Trust boundaries

- The browser talks only to the same-origin Next BFF.
- FastAPI is internal; keep port `8000` unexposed in production.
- The BFF is an edge, not the authorization boundary: FastAPI enforces RBAC on every route.
- Optional services must not be required for the core app to start or serve.
