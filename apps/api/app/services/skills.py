"""
AI Workspace API — Skills Registry

Loads SKILL.md manifests from the skills directory.
"""

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from app.config import settings
from app.models.skill import SkillManifest

logger = logging.getLogger(__name__)


class SkillRegistry:
    """Filesystem-backed registry of agent skills."""

    def __init__(self, directory: Path | str):
        path = Path(directory)
        if not path.is_absolute() and not path.is_dir():
            # Local runs happen from apps/api; fall back to the repo-root skills dir.
            fallback = Path(__file__).resolve().parents[4] / path
            if fallback.is_dir():
                path = fallback
        self._directory = path
        self._skills: dict[str, SkillManifest] = {}
        self._loaded = False

    @property
    def directory(self) -> Path:
        return self._directory

    def load(self) -> None:
        """Reload all valid skills from disk."""
        self._skills.clear()
        if not self._directory.is_dir():
            logger.warning("Skills directory not found: %s", self._directory)
            self._loaded = True
            return

        for path in sorted(self._directory.glob("*/SKILL.md")):
            try:
                manifest = self._parse(path)
            except (ValueError, ValidationError, yaml.YAMLError) as exc:
                logger.warning("Skipping invalid skill %s: %s", path, exc)
                continue
            self._skills[manifest.name] = manifest

        self._loaded = True
        logger.info("Loaded %d skills from %s", len(self._skills), self._directory)

    def _parse(self, path: Path) -> SkillManifest:
        text = path.read_text(encoding="utf-8")
        if not text.lstrip().startswith("---"):
            raise ValueError("missing frontmatter")

        _, frontmatter, body = text.split("---", 2)
        data: dict[str, Any] = yaml.safe_load(frontmatter) or {}
        data["instructions"] = body.strip()
        return SkillManifest.model_validate(data)

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    def list(self) -> list[SkillManifest]:
        self._ensure_loaded()
        return sorted(self._skills.values(), key=lambda skill: skill.name)

    def get(self, name: str) -> SkillManifest | None:
        self._ensure_loaded()
        return self._skills.get(name)


skill_registry = SkillRegistry(settings.skills_dir)
