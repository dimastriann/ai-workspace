# AGENTS.md

Guidance for AI agents and humans working in this repository.

## Project

AI Workspace — a full-stack AI platform (chat, RAG, agents) with:

- `apps/web` — Next.js 16 frontend with a same-origin BFF
- `apps/api` — FastAPI backend (Python 3.13, managed by `uv`)
- `rust/parser` — optional high-performance document parser (Actix)
- `skills/` — agent skills (added in a later phase)

Optional infrastructure must stay optional. See "Architecture guardrails".

## Toolchain

- JavaScript: **pnpm** workspace at the repository root.
- Python: **uv** from `apps/api`.
- Git hooks: **lefthook**. Commit messages: **commitlint** (Conventional Commits).
- TypeScript lint/format: **Biome**. Types: `tsc`.
- Python lint/format: **ruff**. Types: **mypy**. Tests: **pytest**.

## Quality gates

Every commit must leave the repository green. Run the relevant subset before committing:

```bash
# Python (from apps/api)
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest

# Web (from repo root)
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

Pre-commit runs the fast checks; pre-push and CI run everything. A commit is not
allowed if any gate it touches is red.

## Commit protocol — atomic commits

- **One logical change per commit.** If a change spans two concerns, split it.
- **Tests belong with the change** that makes them pass.
- **Every commit passes its gates.** Never commit broken code, `wip`, or commented-out code.
- **Never mix mechanical reformatting with behavior changes.** Put formatting in its own commit.
- Slice features vertically and in small steps: `schema → service → router → tests → UI`.
- Use Conventional Commits: `feat(scope):`, `fix(scope):`, `chore(scope):`, `docs(scope):`,
  `test(scope):`, `refactor(scope):`, `build(scope):`, `ci(scope):`.
- Keep the subject imperative and under ~72 characters. Use the body to explain *why*.
- Do not force-push, rewrite published history, or commit secrets.
- Do not push or open a PR unless explicitly asked.

## Code standards

- Clean, readable, and minimal. Delete dead code instead of leaving it commented out.
- Prefer the smallest solution that is correct and testable.
- Type everything in Python; avoid `Any` unless interfacing with untyped libraries.
- Validate all external input at the boundary (Pydantic models, path params, uploads).
- No blocking I/O inside async handlers; use async drivers or offload with `asyncio.to_thread`.
- Keep business logic in `services/`, transport concerns in `routers/`, persistence in models.
- No new mandatory infrastructure without an explicit decision.

## Security rules

- Never log or return secrets. Secret settings are encrypted at rest and masked in APIs.
- Enforce authorization server-side (RBAC dependency), never only in the UI.
- Use the BFF: the browser talks only to same-origin `/api/*`; the API stays internal.
- Sessions use `httpOnly`, `Secure`, `SameSite=Lax` cookies with hashed opaque tokens.
- Uploads: enforce size, MIME, extension, and path-traversal limits.
- Terminal/IDE features are admin-only, off by default, non-root, and never mount the Docker socket.
- Audit admin actions, logins, and shell/agent execution.

## Architecture guardrails

- **PostgreSQL is the only mandatory service.**
- Redis is optional (cache/rate-limit/queue acceleration).
- Qdrant is optional (semantic retrieval); the default retriever is Postgres full-text search.
- The Rust parser is optional; Python parsers are the fallback.
- Optional capabilities are gated by settings flags and compose profiles.
- Every optional feature must degrade gracefully when its service is absent.

## Testing expectations

- Unit tests for services and pure logic; integration tests for routers using the ASGI client.
- Tests must be deterministic and must not require external services unless explicitly marked.
- Bug fixes include a regression test.
- Prefer covering behavior and contracts over implementation details.

## Development agent skills

Coding-agent skills for building this repository live in `.agents/skills/<name>/SKILL.md`
(repo-scoped, instructions only). They are separate from the product runtime skills in
`skills/`, which the app's agent uses.

- Codex and OpenCode read `.agents/skills` natively.
- Claude Code reads `.claude/skills/<name>/SKILL.md`, which are committed pointers to the
  canonical files. When editing a skill's `name` or `description`, update its pointer too.
- Available: `repo-gates`, `feature-slice`, `api-endpoint`, `db-migration`, `docker-local`.
- `docker-local` is optional: skip cleanly when Docker is unavailable; never block other
  work on it and never run destructive Docker commands without confirmation.
- Invocation: Claude Code `/skill-name`; Codex `$skill-name` or `/skills`; OpenCode
  `/skills` or `@skill-name`.

## Pull request / review checklist

- [ ] Change is scoped and atomic; commit messages explain intent.
- [ ] Lint, format, typecheck, tests, and build pass.
- [ ] Migrations are reversible.
- [ ] No secrets, no debug logging, no commented-out code.
- [ ] Optional services are still optional.
- [ ] Docs or OpenAPI descriptions updated when behavior changes.
