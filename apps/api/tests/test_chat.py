"""
Tests for the Chat router endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_chat_message(client: AsyncClient):
    """POST /api/chat/ should return a stub response."""
    response = await client.post("/api/chat/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "stub"


@pytest.mark.asyncio
async def test_list_chat_sessions(client: AsyncClient):
    """GET /api/chat/sessions should return empty sessions list."""
    response = await client.get("/api/chat/sessions")
    assert response.status_code == 200
    data = response.json()
    assert "sessions" in data
    assert data["sessions"] == []
