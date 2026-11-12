"""
Tests for the Chat router endpoints.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_chat_stream_rejects_empty_payload(member_client: AsyncClient):
    """POST /api/chat/stream should validate the required message field."""
    response = await member_client.post("/api/chat/stream", json={})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_stream_rejects_blank_message(member_client: AsyncClient):
    """A blank message is rejected by request validation."""
    response = await member_client.post("/api/chat/stream", json={"message": ""})

    assert response.status_code == 422
