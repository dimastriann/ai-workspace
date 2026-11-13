---
name: db-migration
description: Add a reversible database migration with the SQLAlchemy model and tests. Use when changing the persisted schema.
license: MIT
compatibility: claude-code,codex,opencode
metadata:
  version: "1.0"
---

# Database migration

1. Update `apps/api/app/models/database.py`.
2. Create the Alembic revision under `apps/api/alembic/versions/` with the correct
   `down_revision`.
3. Implement both `upgrade()` and `downgrade()` so the migration is reversible.
4. Verify offline SQL generation:
   `uv run alembic upgrade head --sql`.
5. Add a persistence test using the SQLite `db_session` fixture.
6. Use `selectinload` for relationships read after a query; never lazy-load in async code.
7. Run the `repo-gates` skill.

## Rules

- Migrations run in order; do not edit an applied revision.
- Keep PostgreSQL-only features (for example GIN expression indexes) out of SQLite tests.
- Destructive changes require a clear downgrade strategy.
