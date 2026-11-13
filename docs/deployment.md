# Deployment

## Prerequisites

- Docker Desktop (or Docker Engine + Compose v2)
- `pnpm` 12 for local tooling
- `uv` for API tooling

## Local stack

```bash
cp .env.example .env
# set APP_SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD
docker compose build
docker compose up -d postgres
docker compose run --rm api alembic upgrade head
docker compose up -d api worker web
```

Open http://localhost:3000 and sign in with the bootstrap admin.

### Optional services

```bash
docker compose --profile optional up -d qdrant parser redis
```

The core app runs without them. Retrieval falls back to Postgres FTS, parsing
falls back to Python, and Redis is only an accelerator.

## Environment

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres connection string |
| `APP_SECRET_KEY` | Session/secret encryption key |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Bootstrap admin on startup |
| `API_BASE_URL` | BFF → FastAPI base URL (`http://api:8000` in compose) |
| `MAX_UPLOAD_MB` | Upload size limit |
| `ALLOWED_UPLOAD_EXTENSIONS` | Comma-separated allowlist |
| `RATE_LIMIT_*` | Sliding-window limits |
| `LOG_LEVEL` / `LOG_JSON` | Logging |

## Migrations

```bash
docker compose run --rm api alembic upgrade head
docker compose run --rm api alembic upgrade head --sql   # offline SQL
```

## PostgreSQL 18 upgrade

The local compose file keeps **Postgres 17** for data-volume compatibility.
To move to 18:

```bash
docker compose exec -T postgres pg_dump -U postgres ai_workspace > backup.sql
docker compose stop postgres
# change the image tag to postgres:18-alpine
docker compose up -d postgres
docker compose exec -T postgres psql -U postgres ai_workspace < backup.sql
```

Major-version data directories are not compatible in place; dump/restore is required.

## Backups

- Database: `pg_dump` as above.
- Uploads: back up the `api_uploads` volume.
- Secrets: store `.env` in a secret manager, never in Git.

## Production notes

- Keep FastAPI on the internal network; expose only the BFF.
- Terminate TLS at the proxy (Caddy/Nginx).
- Run `APP_ENV=production` so cookies are `Secure` and logs are JSON.
- Do not expose the runtime/IDE container without admin-only auth and isolation.
