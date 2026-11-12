"""Map ORM users to public response models."""

from app.models.database import User
from app.models.user import UserResponse


def to_user_response(user: User) -> UserResponse:
    """Map an ORM user to its public representation."""
    return UserResponse(
        id=str(user.id),
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )
