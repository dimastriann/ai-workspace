"""Tests for the agent tool layer."""

import json
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Document, DocumentChunk, Workspace
from app.services.tools import (
    evaluate_expression,
    search_documents_handler,
    tool_registry,
)


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("1 + 2", 3.0),
        ("(2 + 3) * 4", 20.0),
        ("10 / 4", 2.5),
        ("-3 + 1", -2.0),
        ("2 ** 3", 8.0),
        ("10 % 3", 1.0),
    ],
)
def test_evaluate_expression(expression: str, expected: float) -> None:
    assert evaluate_expression(expression) == expected


@pytest.mark.parametrize("expression", ["__import__('os')", "a + 1", "1;2"])
def test_evaluate_expression_rejects_unsafe_input(expression: str) -> None:
    with pytest.raises((ValueError, SyntaxError)):
        evaluate_expression(expression)


def test_registry_filters_by_permission() -> None:
    calculator_only = tool_registry.list_for({"calculator"})
    assert [tool.name for tool in calculator_only] == ["calculator"]

    search_only = tool_registry.list_for({"search_documents"})
    assert [tool.name for tool in search_only] == ["search_documents"]

    assert tool_registry.list_for(set()) == []


def test_tool_schemas_are_openai_compatible() -> None:
    tool = tool_registry.get("calculator")
    assert tool is not None
    schema = tool.to_openai()
    assert schema["type"] == "function"
    assert schema["function"]["parameters"]["required"] == ["expression"]


async def test_search_documents_tool(db_session: AsyncSession) -> None:
    workspace = Workspace(id=uuid.uuid4(), name="Test")
    db_session.add(workspace)
    await db_session.commit()

    document = Document(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        filename="notes.md",
        document_type="markdown",
        size_bytes=10,
        chunk_count=1,
        status="completed",
    )
    db_session.add(document)
    await db_session.commit()

    db_session.add(
        DocumentChunk(
            id=uuid.uuid4(),
            document_id=document.id,
            workspace_id=workspace.id,
            ordinal=0,
            content="alpha beta gamma",
        )
    )
    await db_session.commit()

    result = await search_documents_handler(
        db_session, workspace.id, {"query": "alpha"}
    )

    payload = json.loads(result)
    assert payload[0]["filename"] == "notes.md"
    assert "alpha beta" in payload[0]["content"]


async def test_search_documents_tool_empty(db_session: AsyncSession) -> None:
    result = await search_documents_handler(
        db_session, uuid.uuid4(), {"query": "nothing"}
    )

    assert result == "No matching document chunks."
