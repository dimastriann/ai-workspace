"""Tests for security primitives."""

import pytest

from app.core.security import (
    decrypt_secret,
    encrypt_secret,
    generate_session_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.enums import Role, role_at_least


def test_password_hash_roundtrip() -> None:
    password = "correct horse battery staple"
    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash)
    assert not verify_password("wrong password", password_hash)


def test_invalid_hash_does_not_raise() -> None:
    assert not verify_password("anything", "not-a-valid-hash")


def test_session_tokens_are_unique() -> None:
    first = generate_session_token()
    second = generate_session_token()

    assert first != second
    assert len(first) >= 32


def test_token_hash_is_deterministic_sha256() -> None:
    token = "session-token"

    assert hash_token(token) == hash_token(token)
    assert len(hash_token(token)) == 64


def test_secret_encryption_roundtrip() -> None:
    encrypted = encrypt_secret("super-secret", "app-secret")

    assert encrypted != "super-secret"
    assert decrypt_secret(encrypted, "app-secret") == "super-secret"


def test_secret_encryption_requires_matching_key() -> None:
    encrypted = encrypt_secret("super-secret", "app-secret")

    with pytest.raises(ValueError):
        decrypt_secret(encrypted, "different-secret")


@pytest.mark.parametrize(
    ("actual", "required", "expected"),
    [
        ("admin", Role.ADMIN, True),
        ("admin", Role.MEMBER, True),
        ("member", Role.VIEWER, True),
        ("member", Role.ADMIN, False),
        ("viewer", Role.MEMBER, False),
        ("unknown", Role.VIEWER, False),
    ],
)
def test_role_at_least(actual: str, required: Role, expected: bool) -> None:
    assert role_at_least(actual, required) is expected
