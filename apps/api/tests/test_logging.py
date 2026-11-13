"""Tests for structured logging and request correlation."""

import json
import logging

from httpx import AsyncClient

from app.core.logging import JsonFormatter


def test_json_formatter_includes_extra_fields() -> None:
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "hello", None, None)
    record.request_id = "abc-123"
    record.status = 200
    record.duration_ms = 1.5

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["message"] == "hello"
    assert payload["request_id"] == "abc-123"
    assert payload["status"] == 200
    assert payload["duration_ms"] == 1.5


async def test_request_id_header_is_set(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.headers.get("x-request-id")


async def test_request_id_is_preserved(client: AsyncClient) -> None:
    response = await client.get("/health", headers={"x-request-id": "custom-id"})

    assert response.headers.get("x-request-id") == "custom-id"
