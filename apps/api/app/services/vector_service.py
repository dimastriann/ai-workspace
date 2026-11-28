"""Optional semantic indexing and search backed by Qdrant.

Embeddings come from the configured OpenAI-compatible gateway; chunks are
upserted per document with workspace filters applied at query time. Every
operation degrades gracefully: when the feature is off or Qdrant is
unreachable, callers fall back to lexical retrieval.
"""

import asyncio
from typing import Any
from uuid import UUID

from app.config import settings as app_settings
from app.services.agent_provider import openai_client
from app.services.settings_service import settings_service

COLLECTION = "document_chunks"


class VectorService:
    def __init__(self) -> None:
        self._qdrant: Any | None = None
        self._embedder: Any | None = None

    def set_qdrant(self, client: Any | None) -> None:
        """Replace the Qdrant client (used by tests)."""
        self._qdrant = client

    def set_embedder(self, embedder: Any | None) -> None:
        """Replace the embedding function (used by tests)."""
        self._embedder = embedder

    async def enabled(self, db: Any) -> bool:
        return bool(await settings_service.get("features.vector_rag", db))

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if self._embedder is not None:
            result = self._embedder(texts)
            if asyncio.iscoroutine(result):
                result = await result
            return result
        client = openai_client()
        response = await client.embeddings.create(
            model=app_settings.embedding_model, input=texts
        )
        return [item.embedding for item in response.data]

    async def index_chunks(
        self,
        workspace_id: UUID,
        document_id: UUID,
        chunks: list[tuple[UUID, str]],
        db: Any,
        project_id: UUID | None = None,
    ) -> bool:
        """Embed and upsert document chunks. Returns whether it succeeded."""
        if not chunks or not await self.enabled(db):
            return False
        payload: dict[str, str] = {
            "workspace_id": str(workspace_id),
            "document_id": str(document_id),
        }
        if project_id is not None:
            payload["project_id"] = str(project_id)
        try:
            vectors = await self.embed([content for _, content in chunks])
            client = await self._qdrant_client()
            await self._ensure_collection(client)
            await client.delete(
                COLLECTION,
                points_selector=self._document_filter(document_id),
            )
            await client.upsert(
                COLLECTION,
                points=[
                    {
                        "id": str(chunk_id),
                        "vector": vector,
                        "payload": payload,
                    }
                    for (chunk_id, _), vector in zip(chunks, vectors, strict=True)
                ],
            )
            return True
        except Exception:
            return False

    async def remove_document(self, document_id: UUID) -> None:
        """Best-effort removal of a document's points."""
        try:
            client = await self._qdrant_client()
            await client.delete(
                COLLECTION,
                points_selector=self._document_filter(document_id),
            )
        except Exception:
            pass

    async def search(
        self,
        workspace_id: UUID,
        query: str,
        limit: int,
        project_id: UUID | None = None,
    ) -> list[tuple[str, float]] | None:
        """Return (chunk_id, score) hits, or None when unavailable."""
        must: list[dict[str, Any]] = [
            {
                "key": "workspace_id",
                "match": {"value": str(workspace_id)},
            }
        ]
        if project_id is not None:
            must.append({"key": "project_id", "match": {"value": str(project_id)}})
        try:
            vectors = await self.embed([query])
            client = await self._qdrant_client()
            response = await client.query_points(
                COLLECTION,
                query=vectors[0],
                query_filter={"must": must},
                limit=limit,
                with_payload=False,
            )
            return [(str(point.id), float(point.score)) for point in response.points]
        except Exception:
            return None

    async def _qdrant_client(self) -> Any:
        if self._qdrant is None:
            from qdrant_client import AsyncQdrantClient

            self._qdrant = AsyncQdrantClient(
                url=app_settings.qdrant_url,
                check_compatibility=False,
            )
        return self._qdrant

    @staticmethod
    async def _ensure_collection(client: Any) -> None:
        from qdrant_client import models

        if not await client.collection_exists(COLLECTION):
            await client.create_collection(
                collection_name=COLLECTION,
                vectors_config=models.VectorParams(
                    size=app_settings.embedding_dimension,
                    distance=models.Distance.COSINE,
                ),
            )

    @staticmethod
    def _document_filter(document_id: UUID) -> dict[str, Any]:
        return {
            "must": [
                {
                    "key": "document_id",
                    "match": {"value": str(document_id)},
                }
            ]
        }


vector_service = VectorService()
