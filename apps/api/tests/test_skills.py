"""Tests for the skills registry and endpoints."""

from pathlib import Path

from httpx import AsyncClient

from app.services.skills import SkillRegistry


def _write_skill(directory: Path, name: str, body: str) -> None:
    skill_dir = directory / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(body, encoding="utf-8")


def test_registry_loads_manifests(tmp_path: Path) -> None:
    _write_skill(
        tmp_path,
        "summarize",
        (
            "---\n"
            "name: summarize\n"
            "description: Summarize docs.\n"
            "permissions:\n"
            "  - search_documents\n"
            "---\n\n"
            "Be concise.\n"
        ),
    )

    registry = SkillRegistry(tmp_path)
    registry.load()

    skills = registry.list()
    assert len(skills) == 1
    assert skills[0].name == "summarize"
    assert skills[0].permissions == ["search_documents"]
    assert skills[0].instructions == "Be concise."


def test_registry_skips_invalid_skills(tmp_path: Path) -> None:
    _write_skill(tmp_path, "valid", "---\nname: valid\ndescription: ok\n---\nbody")
    _write_skill(tmp_path, "invalid", "no frontmatter here")

    registry = SkillRegistry(tmp_path)
    registry.load()

    assert [skill.name for skill in registry.list()] == ["valid"]


def test_registry_missing_directory_is_empty(tmp_path: Path) -> None:
    registry = SkillRegistry(tmp_path / "missing")
    registry.load()

    assert registry.list() == []
    assert registry.get("anything") is None


def test_repo_skills_load() -> None:
    registry = SkillRegistry(Path("../../skills"))
    registry.load()

    names = {skill.name for skill in registry.list()}
    assert {"summarize", "investigate"}.issubset(names)


async def test_skills_endpoint(member_client: AsyncClient) -> None:
    response = await member_client.get("/api/skills")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
