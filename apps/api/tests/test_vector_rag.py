"""Tests for optional Qdrant-backed semantic retrieval."""

import uuid
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Document, DocumentChunk, Workspace
from app.services.retrieval import retrieval_service
from app.services.settings_service import settings_service
from app.services.vector_service import vector_service


class FakeQdrant:
    """Minimal in-memory stand-in for the async Qdrant client."""

    def __init__(self) -> None:
        self.points: dict[str, dict[str, Any]] = {}
        self.collection_created = False

    async def collection_exists(self, name: str) -> bool:
        return self.collection_created

    async def create_collection(self, **kwargs: Any) -> None:
        self.collection_created = True

    async def upsert(self, collection: str, points: list[dict[str, Any]]) -> None:
        for point in points:
            self.points[str(point["id"])] = point

    async def delete(self, collection: str, points_selector: dict[str, Any]) -> None:
        target = points_selector["must"][0]["match"]["value"]
        self.points = {
            point_id: point
            for point_id, point in self.points.items()
            if point["payload"]["document_id"] != target
        }

    async def query_points(
        self,
        collection: str,
        query: list[float],
        query_filter: dict[str, Any],
        limit: int,
        with_payload: bool = False,
    ) -> Any:
        wanted = query_filter["must"][0]["match"]["value"]

        class Point:
            def __init__(self, point_id: str) -> None:
                self.id = point_id
                self.score = 0.9

        matches = [
            point_id
            for point_id, point in self.points.items()
            if point["payload"]["workspace_id"] == wanted
        ]
        return type("Response", (), {"points": [Point(p) for p in matches[:limit]]})()


def fake_embedder(dimension: int = 8):
    def embed(texts: list[str]) -> list[list[float]]:
        return [[float(len(text) % dimension)] * dimension for text in texts]

    return embed


@pytest.fixture
def fake_vector(monkeypatch: pytest.MonkeyPatch) -> FakeQdrant:
    qdrant = FakeQdrant()
    monkeypatch.setattr(vector_service, "_qdrant", qdrant, raising=False)
    monkeypatch.setattr(vector_service, "_embedder", fake_embedder())
    return qdrant


async def _seed_document(db: AsyncSession, workspace_id: uuid.UUID) -> Document:
    document = Document(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        filename="notes.md",
        document_type="markdown",
        size_bytes=10,
        chunk_count=2,
        status="completed",
    )
    db.add(document)
    await db.commit()
    return document


async def test_index_chunks_disabled_by_default(
    db_session: AsyncSession, fake_vector: FakeQdrant
) -> None:
    workspace = Workspace(id=uuid.uuid4(), name="W")
    db_session.add(workspace)
    await db_session.commit()

    indexed = await vector_service.index_chunks(
        workspace.id, uuid.uuid4(), [(uuid.uuid4(), "text")], db_session
    )

    assert indexed is False
    assert not fake_vector.points


async def test_index_chunks_upserts_and_search_returns_content(
    db_session: AsyncSession, fake_vector: FakeQdrant
) -> None:
    workspace = Workspace(id=uuid.uuid4(), name="W")
    db_session.add(workspace)
    await db_session.commit()
    document = await _seed_document(db_session, workspace.id)
    await settings_service.set("features.vector_rag", True, db_session)

    chunk_ids = [uuid.uuid4(), uuid.uuid4()]
    db_session.add_all(
        [
            DocumentChunk(
                id=chunk_ids[0],
                document_id=document.id,
                workspace_id=workspace.id,
                ordinal=0,
                content="alpha content",
            ),
            DocumentChunk(
                id=chunk_ids[1],
                document_id=document.id,
                workspace_id=workspace.id,
                ordinal=1,
                content="beta content",
            ),
        ]
    )
    await db_session.commit()

    indexed = await vector_service.index_chunks(
        workspace.id,
        document.id,
        [(chunk_ids[0], "alpha content"), (chunk_ids[1], "beta content")],
        db_session,
    )
    assert indexed is True
    assert len(fake_vector.points) == 2

    hits = await vector_service.search(workspace.id, "alpha", limit=5)
    assert hits is not None and len(hits) == 2

    chunks = await retrieval_service.search("alpha", workspace.id, db_session)
    assert len(chunks) == 2
    assert {chunk.content for chunk in chunks} == {"alpha content", "beta content"}
    assert all(chunk.filename == "notes.md" for chunk in chunks)


async def test_reingestion_replaces_document_points(
    db_session: AsyncSession, fake_vector: FakeQdrant
) -> None:
    workspace = Workspace(id=uuid.uuid4(), name="W")
    db_session.add(workspace)
    await db_session.commit()
    await settings_service.set("features.vector_rag", True, db_session)

    document_id = uuid.uuid4()
    await vector_service.index_chunks(
        workspace.id, document_id, [(uuid.uuid4(), "old")], db_session
    )
    await vector_service.index_chunks(
        workspace.id, document_id, [(uuid.uuid4(), "new")], db_session
    )

    assert len(fake_vector.points) == 1


async def test_remove_document_deletes_points(
    db_session: AsyncSession, fake_vector: FakeQdrant
) -> None:
    workspace = Workspace(id=uuid.uuid4(), name="W")
    db_session.add(workspace)
    await db_session.commit()
    await settings_service.set("features.vector_rag", True, db_session)
    document_id = uuid.uuid4()
    await vector_service.index_chunks(
        workspace.id, document_id, [(uuid.uuid4(), "text")], db_session
    )
    assert len(fake_vector.points) == 1

    await vector_service.remove_document(document_id)

    assert not fake_vector.points


async def test_search_falls_back_to_lexical_on_qdrant_error(
    db_session: AsyncSession, fake_vector: FakeQdrant
) -> None:
    workspace = Workspace(id=uuid.uuid4(), name="W")
    db_session.add(workspace)
    await db_session.commit()
    document = await _seed_document(db_session, workspace.id)
    db_session.add(
        DocumentChunk(
            document_id=document.id,
            workspace_id=workspace.id,
            ordinal=0,
            content="unique fallback text",
        )
    )
    await db_session.commit()
    await settings_service.set("features.vector_rag", True, db_session)

    async def broken_search(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("qdrant down")

    monkeypatch_query = broken_search
    fake_vector.query_points = monkeypatch_query  # type: ignore[method-assign]

    chunks = await retrieval_service.search("fallback", workspace.id, db_session)

    assert len(chunks) == 1
    assert chunks[0].content == "unique fallback text"
