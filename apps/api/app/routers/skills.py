"""
AI Workspace API — Skills Router

Lists available skills for the current user.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import require_member, require_viewer
from app.models.database import User
from app.models.skill import SkillDetail, SkillSummary
from app.services.skills import skill_registry

router = APIRouter()


@router.get("", response_model=list[SkillSummary])
async def list_skills(_user: User = Depends(require_viewer)) -> list[SkillSummary]:
    """List available skills."""
    return [
        SkillSummary(
            name=skill.name,
            description=skill.description,
            permissions=skill.permissions,
            version=skill.version,
        )
        for skill in skill_registry.list()
    ]


@router.get("/{name}", response_model=SkillDetail)
async def get_skill(name: str, _user: User = Depends(require_member)) -> SkillDetail:
    """Return a skill manifest and its instructions."""
    skill = skill_registry.get(name)
    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found"
        )
    return SkillDetail(**skill.model_dump())
