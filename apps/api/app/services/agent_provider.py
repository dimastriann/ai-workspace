"""
AI Workspace API — Agent Provider

Thin OpenAI-compatible streaming client with tool-call support.
"""

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Protocol, cast

from openai import AsyncOpenAI

from app.config import settings


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ProviderEvent:
    type: str  # "token" | "tool_calls" | "done"
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


class AgentProvider(Protocol):
    """Streaming provider interface used by the executor."""

    def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> AsyncIterator[ProviderEvent]: ...


class OpenAIProvider:
    """Stream chat completions and tool calls from an OpenAI-compatible API."""

    def __init__(self) -> None:
        kwargs: dict[str, Any] = {
            "api_key": settings.openai_api_key or "missing",
        }
        if settings.llm_provider == "ollama":
            kwargs["base_url"] = f"{settings.ollama_base_url.rstrip('/')}/v1"
            kwargs["api_key"] = settings.openai_api_key or "ollama"

        self._client = AsyncOpenAI(**kwargs)
        self._model = settings.openai_model

    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> AsyncIterator[ProviderEvent]:
        stream: Any = await self._client.chat.completions.create(
            model=self._model,
            messages=cast(Any, messages),
            tools=cast(Any, tools or None),
            stream=True,
        )

        pending: dict[int, dict[str, str]] = {}
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta

            if delta.content:
                yield ProviderEvent(type="token", content=delta.content)

            for tool_delta in delta.tool_calls or []:
                entry = pending.setdefault(
                    tool_delta.index, {"id": "", "name": "", "arguments": ""}
                )
                if tool_delta.id:
                    entry["id"] = tool_delta.id
                if tool_delta.function:
                    if tool_delta.function.name:
                        entry["name"] += tool_delta.function.name
                    if tool_delta.function.arguments:
                        entry["arguments"] += tool_delta.function.arguments

        if pending:
            calls: list[ToolCall] = []
            for index in sorted(pending):
                entry = pending[index]
                try:
                    arguments = json.loads(entry["arguments"] or "{}")
                except json.JSONDecodeError:
                    arguments = {}
                calls.append(
                    ToolCall(
                        id=entry["id"] or f"call_{index}",
                        name=entry["name"],
                        arguments=arguments,
                    )
                )
            yield ProviderEvent(type="tool_calls", tool_calls=calls)

        yield ProviderEvent(type="done")


def get_provider() -> OpenAIProvider:
    """Build the configured provider."""
    return OpenAIProvider()
