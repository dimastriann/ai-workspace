"""Tests for provider construction."""

from openai import AsyncOpenAI

from app.config import settings as app_settings
from app.services.agent_provider import OpenAIProvider, get_provider


async def test_default_provider_targets_openai() -> None:
    provider = get_provider()
    expected = str(AsyncOpenAI(api_key="missing").base_url).rstrip("/")
    assert str(provider._client.base_url).rstrip("/") == expected


async def test_gemini_provider_uses_compatible_endpoint(
    monkeypatch,
) -> None:
    monkeypatch.setattr(app_settings, "llm_provider", "gemini")
    monkeypatch.setattr(app_settings, "openai_api_key", "gemini-key-123")

    provider = OpenAIProvider(model="gemini-2.5-flash")

    assert (
        str(provider._client.base_url)
        .rstrip("/")
        .endswith("generativelanguage.googleapis.com/v1beta/openai")
    )
    assert provider._model == "gemini-2.5-flash"


async def test_ollama_provider_appends_v1(monkeypatch) -> None:
    monkeypatch.setattr(app_settings, "llm_provider", "ollama")
    monkeypatch.setattr(app_settings, "ollama_base_url", "http://ollama:11434/")

    provider = OpenAIProvider()

    assert str(provider._client.base_url).rstrip("/") == "http://ollama:11434/v1"
