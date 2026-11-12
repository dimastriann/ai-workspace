"""
AI Workspace API — Retrieval

Lexical context retrieval backed by Postgres full-text search.
Falls back to a simple match on non-Postgres databases (tests).
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import DocumentChunk


class RetrievalService:
    """Return relevant document chunks for a workspace."""

    async def search(
        self,
        query: str,
        workspace_id: UUID,
        db: AsyncSession,
        limit: int = 5,
    ) -> list[str]:
        if not query.strip():
            return []

        dialect = db.get_bind().dialect.name
        if dialect == "postgresql":
            ts_query = func.plainto_tsquery("english", query)
            ts_vector = func.to_tsvector("english", DocumentChunk.content)
            statement = (
                select(DocumentChunk.content)
                .where(DocumentChunk.workspace_id == workspace_id)
                .where(ts_vector.op("@@")(ts_query))
                .order_by(func.ts_rank(ts_vector, ts_query).desc())
                .limit(limit)
            )
        else:
            statement = (
                select(DocumentChunk.content)
                .where(DocumentChunk.workspace_id == workspace_id)
                .where(DocumentChunk.content.ilike(f"%{query}%"))
                .order_by(DocumentChunk.ordinal)
                .limit(limit)
            )

        result = await db.execute(statement)
        return list(result.scalars().all())


retrieval_service = RetrievalService()
