---
name: repo-gates
description: Run the repository's required quality gates before committing or pushing. Use when finishing a change, preparing a commit, or validating the repository.
license: MIT
compatibility: claude-code,codex,opencode
metadata:
  version: "1.0"
---

# Repository gates

Run every gate the change touches. Never commit or push while a gate is red.

## Backend (from `apps/api`)

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest
```

## Web (from the repository root)

```bash
pnpm install --frozen-lockfile
pnpm lint
pnpm typecheck
pnpm build
```

## Rust parser (optional)

```bash
cd rust/parser
cargo fmt --check
cargo clippy --all-targets -- -D warnings
cargo test
```

## Compose

```bash
docker compose config
```

If the Docker CLI is not installed, skip this step and say so explicitly.

## Report

Report pass/fail per gate with the exact command that was run. Do not hide failures,
do not skip a gate silently, and do not commit while any gate is red.
