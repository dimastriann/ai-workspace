"""
AI Workspace API — Document Ingestion Handler

Parses an uploaded document, embeds its chunks, and indexes them.
Run by the Postgres-backed worker.
"""

import os
from typing import Any
from uuid import UUID

import httpx
from qdrant_client.models import Distance, PointStruct, VectorParams
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.vector_store import get_collection_name, qdrant_client
from app.models.database import Document
from app.services.embedding_service import embedding_service


async def process_document(db: AsyncSession, payload: dict[str, Any]) -> None:
    """Handle a document ingestion job."""
    document_id = UUID(str(payload["document_id"]))
    workspace_id = UUID(str(payload["workspace_id"]))
    file_path = str(payload["file_path"])

    try:
        chunks = await _parse(file_path)
        await _index(workspace_id, document_id, chunks)

        document = await db.get(Document, document_id)
        if document is not None:
            document.status = "completed"
            document.chunk_count = len(chunks)
            await db.commit()
    except Exception:
        document = await db.get(Document, document_id)
        if document is not None:
            document.status = "error"
            await db.commit()
        raise


async def _parse(file_path: str) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        with open(file_path, "rb") as handle:
            files = {"file": (os.path.basename(file_path), handle)}
            response = await client.post(
                f"{settings.parser_service_url}/parse", files=files
            )

    if response.status_code != 200:
        raise RuntimeError(f"Parser returned {response.status_code}")

    chunks: list[dict[str, Any]] = response.json().get("chunks", [])
    if not chunks:
        raise RuntimeError("Parser returned no chunks")
    return chunks


async def _index(
    workspace_id: UUID,
    document_id: UUID,
    chunks: list[dict[str, Any]],
) -> None:
    embeddings = await embedding_service.embed_documents(
        [chunk["content"] for chunk in chunks]
    )
    collection_name = get_collection_name(str(workspace_id))

    collections = qdrant_client.get_collections().collections
    if not any(collection.name == collection_name for collection in collections):
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=settings.embedding_dimension, distance=Distance.COSINE
            ),
        )

    points = [
        PointStruct(
            id=str(chunk["id"]),
            vector=embeddings[index],
            payload={
                "document_id": str(document_id),
                "workspace_id": str(workspace_id),
                "content": chunk["content"],
                "chunk_index": chunk["chunk_index"],
                "metadata": chunk.get("metadata", {}),
            },
        )
        for index, chunk in enumerate(chunks)
    ]

    qdrant_client.upsert(collection_name=collection_name, points=points)
