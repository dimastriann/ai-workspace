"""
AI Workspace API — Settings Service

Typed runtime settings with defaults, validation, and secret encryption.
"""

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.core.security import decrypt_secret, encrypt_secret
from app.models.database import AppSetting


class SettingType(StrEnum):
    """Supported setting value types."""

    STRING = "string"
    BOOL = "bool"
    INT = "int"


@dataclass(frozen=True)
class SettingSpec:
    """Definition of a single setting."""

    key: str
    type: SettingType
    default: str | bool | int
    is_secret: bool = False


SETTINGS: dict[str, SettingSpec] = {
    "features.qdrant": SettingSpec("features.qdrant", SettingType.BOOL, False),
    "features.redis": SettingSpec("features.redis", SettingType.BOOL, False),
    "features.terminal": SettingSpec("features.terminal", SettingType.BOOL, False),
    "features.code_server": SettingSpec(
        "features.code_server", SettingType.BOOL, False
    ),
    "features.agent_shell": SettingSpec(
        "features.agent_shell", SettingType.BOOL, False
    ),
    "features.vector_rag": SettingSpec("features.vector_rag", SettingType.BOOL, False),
    "rag.retriever": SettingSpec("rag.retriever", SettingType.STRING, "postgres"),
    "llm.provider": SettingSpec("llm.provider", SettingType.STRING, "openai"),
    "llm.openai_model": SettingSpec("llm.openai_model", SettingType.STRING, "gpt-4o"),
    "llm.openai_api_key": SettingSpec(
        "llm.openai_api_key", SettingType.STRING, "", is_secret=True
    ),
}

SECRET_MASK = "********"


def _validate(spec: SettingSpec, value: Any) -> None:
    if spec.type is SettingType.BOOL and not isinstance(value, bool):
        raise ValueError(f"{spec.key} must be a boolean")
    if spec.type is SettingType.INT and (
        not isinstance(value, int) or isinstance(value, bool)
    ):
        raise ValueError(f"{spec.key} must be an integer")
    if spec.type is SettingType.STRING and not isinstance(value, str):
        raise ValueError(f"{spec.key} must be a string")


def _encode(spec: SettingSpec, value: Any) -> str:
    serialized = json.dumps(value)
    if spec.is_secret:
        return encrypt_secret(serialized, app_settings.app_secret_key)
    return serialized


def _decode(spec: SettingSpec, raw: str) -> Any:
    serialized = (
        decrypt_secret(raw, app_settings.app_secret_key) if spec.is_secret else raw
    )
    return json.loads(serialized)


class SettingsService:
    """Read and write runtime settings."""

    def spec(self, key: str) -> SettingSpec:
        try:
            return SETTINGS[key]
        except KeyError as exc:
            raise KeyError(f"Unknown setting: {key}") from exc

    async def get_all(self, db: AsyncSession) -> dict[str, Any]:
        result = await db.execute(select(AppSetting))
        rows = {row.key: row for row in result.scalars().all()}

        values: dict[str, Any] = {}
        for key, spec in SETTINGS.items():
            row = rows.get(key)
            values[key] = _decode(spec, row.value) if row else spec.default
        return values

    async def get(self, key: str, db: AsyncSession) -> Any:
        spec = self.spec(key)
        row = await db.get(AppSetting, key)
        return _decode(spec, row.value) if row else spec.default

    async def set(
        self,
        key: str,
        value: Any,
        db: AsyncSession,
        *,
        updated_by: UUID | None = None,
    ) -> Any:
        spec = self.spec(key)
        _validate(spec, value)

        row = await db.get(AppSetting, key)
        encoded = _encode(spec, value)
        if row is None:
            db.add(
                AppSetting(
                    key=key,
                    value=encoded,
                    value_type=spec.type.value,
                    is_secret=spec.is_secret,
                    updated_by=updated_by,
                )
            )
        else:
            row.value = encoded
            row.updated_by = updated_by

        await db.commit()
        return value

    async def public_flags(self, db: AsyncSession) -> dict[str, bool]:
        values = await self.get_all(db)
        return {
            key: bool(value)
            for key, value in values.items()
            if key.startswith("features.")
        }


settings_service = SettingsService()
