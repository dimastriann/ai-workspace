"""Skill manifest models."""

from pydantic import BaseModel, Field


class SkillManifest(BaseModel):
    """A skill loaded from a SKILL.md file."""

    name: str = Field(..., pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")
    description: str = Field(..., min_length=1, max_length=500)
    permissions: list[str] = Field(default_factory=list)
    version: str = "1.0"
    instructions: str = ""


class SkillSummary(BaseModel):
    """Skill metadata without the full instructions."""

    name: str
    description: str
    permissions: list[str]
    version: str


class SkillDetail(SkillSummary):
    """Skill metadata plus its instructions."""

    instructions: str
