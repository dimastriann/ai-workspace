"""
AI Workspace API — Retrieval

Lexical context retrieval backed by Postgres full-text search.
Falls back to a simple match on non-Postgres databases (tests).
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Document, DocumentChunk


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
