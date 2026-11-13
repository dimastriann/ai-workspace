---
name: api-endpoint
description: Add or change a FastAPI endpoint with schema, service, authorization, tests, and a matching BFF route and query hook. Use when exposing new API behavior.
license: MIT
compatibility: claude-code,codex,opencode
metadata:
  version: "1.0"
---

# API endpoint

1. Validate input at the boundary with Pydantic models in `apps/api/app/models/`.
2. Put business logic in `apps/api/app/services/`; keep routers thin.
3. Enforce authorization server-side with `require_viewer`, `require_member`, or
   `require_admin` from `app.dependencies`. Never rely on the UI.
4. Add a reversible Alembic migration if persistence changes.
5. Add pytest coverage using the ASGI client and the `db_session`, `member_client`, or
   `viewer_client` fixtures. Cover 401/403 where relevant.
6. Expose the endpoint through the Next BFF in `apps/web/app/api/.../route.ts`. Use
   `proxyWithCookies` or `proxyFormWithCookies` when the session cookie is required.
7. Add or update the TanStack Query hook in `apps/web/lib/queries/` and the types in
   `apps/web/lib/types.ts`.
8. Update OpenAPI descriptions when behavior changes.
9. Run the `repo-gates` skill.

## Notes

- The browser only calls same-origin `/api/*` on the Next BFF.
- FastAPI stays internal; never expose secrets or raw upstream errors.
- Use `selectinload` for relationships to avoid async lazy-load errors.
