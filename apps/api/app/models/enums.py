"""Shared enums for the application."""

from enum import StrEnum


class Role(StrEnum):
    """User roles, ordered from least to most privileged."""

    VIEWER = "viewer"
    MEMBER = "member"
    ADMIN = "admin"


_ROLE_RANK: dict[Role, int] = {
    Role.VIEWER: 1,
    Role.MEMBER: 2,
    Role.ADMIN: 3,
}


def role_at_least(actual: str, required: Role) -> bool:
    """Return whether ``actual`` is at least as privileged as ``required``."""
    try:
        actual_role = Role(actual)
    except ValueError:
        return False
    return _ROLE_RANK[actual_role] >= _ROLE_RANK[required]
