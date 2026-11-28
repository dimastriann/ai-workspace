"""
AI Workspace API — Retrieval

Semantic retrieval backed by Qdrant when enabled, falling back to
Postgres full-text search (and a simple match on non-Postgres databases
for tests) whenever the vector path is unavailable.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Document, DocumentChunk
from app.services.vector_service import vector_service


@dataclass(frozen=True)
class RetrievedChunk:
    """A chunk returned by retrieval, with its source document."""

    document_id: str
    filename: str
    ordinal: int
    content: str


class RetrievalService:
    """Return relevant document chunks for a workspace."""

    async def search(
        self,
        query: str,
        workspace_id: UUID,
        db: AsyncSession,
        limit: int = 5,
    ) -> list[RetrievedChunk]:
        if not query.strip():
            return []

        semantic = await self._semantic_search(query, workspace_id, db, limit)
        if semantic is not None:
            return semantic

        return await self._lexical_search(query, workspace_id, db, limit)

    async def _semantic_search(
        self,
        query: str,
        workspace_id: UUID,
        db: AsyncSession,
        limit: int,
    ) -> list[RetrievedChunk] | None:
        """Vector search; None means fall back to lexical."""
        if not await vector_service.enabled(db):
            return None
        hits = await vector_service.search(workspace_id, query, limit)
        if hits is None:
            return None
        if not hits:
            return []

        statement = (
            select(
                DocumentChunk.id,
                DocumentChunk.document_id,
                DocumentChunk.ordinal,
                DocumentChunk.content,
                Document.filename,
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(DocumentChunk.id.in_([UUID(chunk_id) for chunk_id, _score in hits]))
        )
        rows = {str(row.id): row for row in (await db.execute(statement)).all()}
        # Qdrant returns hits in relevance order; preserve it.
        return [
            RetrievedChunk(
                document_id=str(row.document_id),
                filename=row.filename,
                ordinal=row.ordinal,
                content=row.content,
            )
            for chunk_id, _score in hits
            if (row := rows.get(chunk_id)) is not None
        ]

    async def _lexical_search(
        self,
        query: str,
        workspace_id: UUID,
        db: AsyncSession,
        limit: int,
    ) -> list[RetrievedChunk]:
        columns = (
            DocumentChunk.document_id,
            DocumentChunk.ordinal,
            DocumentChunk.content,
            Document.filename,
        )

        dialect = db.get_bind().dialect.name
        if dialect == "postgresql":
            ts_query = func.plainto_tsquery("english", query)
            ts_vector = func.to_tsvector("english", DocumentChunk.content)
            statement = (
                select(*columns)
                .join(Document, Document.id == DocumentChunk.document_id)
                .where(DocumentChunk.workspace_id == workspace_id)
                .where(ts_vector.op("@@")(ts_query))
                .order_by(func.ts_rank(ts_vector, ts_query).desc())
                .limit(limit)
            )
        else:
            statement = (
                select(*columns)
                .join(Document, Document.id == DocumentChunk.document_id)
                .where(DocumentChunk.workspace_id == workspace_id)
                .where(DocumentChunk.content.ilike(f"%{query}%"))
                .order_by(DocumentChunk.ordinal)
                .limit(limit)
            )

        rows = (await db.execute(statement)).all()
        return [
            RetrievedChunk(
                document_id=str(row.document_id),
                filename=row.filename,
                ordinal=row.ordinal,
                content=row.content,
            )
            for row in rows
        ]


retrieval_service = RetrievalService()
