"""Tests for the settings service."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AppSetting
from app.services.settings_service import settings_service


async def test_defaults_are_returned(db_session: AsyncSession) -> None:
    values = await settings_service.get_all(db_session)

    assert values["features.qdrant"] is False
    assert values["features.terminal"] is False
    assert values["rag.retriever"] == "postgres"


async def test_set_and_get_value(db_session: AsyncSession) -> None:
    await settings_service.set("features.qdrant", True, db_session)

    assert await settings_service.get("features.qdrant", db_session) is True

    values = await settings_service.get_all(db_session)
    assert values["features.qdrant"] is True


async def test_secret_is_encrypted_at_rest(db_session: AsyncSession) -> None:
    secret = "sk-test-value"
    await settings_service.set("llm.openai_api_key", secret, db_session)

    row = await db_session.get(AppSetting, "llm.openai_api_key")
    assert row is not None
    assert row.is_secret is True
    assert secret not in row.value

    assert await settings_service.get("llm.openai_api_key", db_session) == secret


async def test_unknown_setting_is_rejected(db_session: AsyncSession) -> None:
    with pytest.raises(KeyError):
        await settings_service.set("nope", True, db_session)


async def test_wrong_type_is_rejected(db_session: AsyncSession) -> None:
    with pytest.raises(ValueError):
        await settings_service.set("features.qdrant", "yes", db_session)

    with pytest.raises(ValueError):
        await settings_service.set("rag.retriever", True, db_session)


async def test_public_flags_only_exposes_features(db_session: AsyncSession) -> None:
    flags = await settings_service.public_flags(db_session)

    assert flags
    assert all(key.startswith("features.") for key in flags)
    assert flags["features.qdrant"] is False


async def test_set_persists_single_row_per_key(db_session: AsyncSession) -> None:
    await settings_service.set("features.redis", True, db_session)
    await settings_service.set("features.redis", False, db_session)

    rows = (await db_session.execute(select(AppSetting))).scalars().all()
    assert len(rows) == 1
    assert await settings_service.get("features.redis", db_session) is False
