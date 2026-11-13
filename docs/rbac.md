# RBAC Matrix

## Roles

| Role | Intent |
|---|---|
| `viewer` | Read-only access to workspaces, documents, and chat history |
| `member` | Upload documents, chat, and run agents |
| `admin` | Manage users, settings, skills, and future runtime features |

## Endpoint permissions

| Endpoint | viewer | member | admin |
|---|---|---|---|
| `GET /auth/me` | ✅ | ✅ | ✅ |
| `POST /auth/logout` | ✅ | ✅ | ✅ |
| `GET /workspaces` | ✅ | ✅ | ✅ |
| `GET /workspaces/{id}` | ✅ | ✅ | ✅ |
| `POST /workspaces` | — | ✅ | ✅ |
| `GET /documents/{workspace_id}` | ✅ | ✅ | ✅ |
| `POST /documents/upload/{workspace_id}` | — | ✅ | ✅ |
| `POST /chat/stream` | — | ✅ | ✅ |
| `POST /agents/runs` | — | ✅ | ✅ |
| `GET /agents/runs` | — | ✅ | ✅ |
| `GET /agents/runs/{id}` | — | ✅ | ✅ (or owner) |
| `GET /skills` | ✅ | ✅ | ✅ |
| `GET /skills/{name}` | — | ✅ | ✅ |
| `GET /settings` | — | — | ✅ |
| `PUT /settings/{key}` | — | — | ✅ |
| `GET /users` | — | — | ✅ |
| `POST /users` | — | — | ✅ |
| `PATCH /users/{id}` | — | — | ✅ |

`POST /users/me/password` is available to every authenticated user.

## Enforcement rules

- Authorization is enforced in FastAPI dependencies (`require_viewer`,
  `require_member`, `require_admin`), never only in the UI.
- The Next BFF forwards the session cookie; it does not make authorization decisions.
- Admin actions and logins are written to `audit_log`.
- Future terminal/IDE features are admin-only, disabled by default, and must not mount
  the Docker socket.
