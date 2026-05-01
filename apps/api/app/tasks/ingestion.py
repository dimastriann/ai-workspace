"""
AI Workspace API — Ingestion Tasks

Taskiq workers for processing uploaded documents:
1. Call Rust parser to extract and chunk text.
2. Generate embeddings for chunks.
3. Upsert into Qdrant vector database.
4. Update document metadata in PostgreSQL.
"""

import httpx
from uuid import UUID
from typing import Any, Dict

from taskiq import TaskiqDepends
from qdrant_client.models import PointStruct, VectorParams, Distance

from app.tasks.broker import broker
from app.config import settings
from app.core.database import get_db_session
from app.core.vector_store import qdrant_client, get_collection_name
from app.models.database import Document
from app.services.embedding_service import embedding_service


@broker.task
async def process_document(document_id: UUID, workspace_id: UUID, file_path: str) -> bool:
    """
    Background task to process an uploaded document.
    """
    # ── 1. Call Rust Parser ──────────────────────────────────────────────────
    async with httpx.AsyncClient(timeout=30.0) as client:
        with open(file_path, "rb") as f:
            files = {"file": (file_path.split("/")[-1], f)}
            response = await client.post(
                f"{settings.parser_service_url}/parse",
                files=files
            )
            
    if response.status_code != 200:
        # Update status to error in DB (manual session management in task)
        return False

    parsed_data = response.json()
    chunks = parsed_data.get("chunks", [])
    
    if not chunks:
        return False

    # ── 2. Generate Embeddings ───────────────────────────────────────────────
    chunk_texts = [c["content"] for c in chunks]
    embeddings = await embedding_service.embed_documents(chunk_texts)

    # ── 3. Initialize Qdrant Collection ───────────────────────────────────────
    collection_name = get_collection_name(str(workspace_id))
    
    # Check if collection exists, if not create it
    collections = qdrant_client.get_collections().collections
    if not any(c.name == collection_name for c in collections):
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=settings.embedding_dimension, 
                distance=Distance.COSINE
            ),
        )

    # ── 4. Upsert to Qdrant ──────────────────────────────────────────────────
    points = [
        PointStruct(
            id=str(chunks[i]["id"]),
            vector=embeddings[i],
            payload={
                "document_id": str(document_id),
                "workspace_id": str(workspace_id),
                "content": chunks[i]["content"],
                "chunk_index": chunks[i]["chunk_index"],
                "metadata": chunks[i].get("metadata", {})
            }
        )
        for i in range(len(chunks))
    ]
    
    qdrant_client.upsert(
        collection_name=collection_name,
        points=points
    )

    # ── 5. Update PostgreSQL ─────────────────────────────────────────────────
    # Since we're in a background task, we open a fresh session
    from app.core.database import async_session
    async with async_session() as session:
        from sqlalchemy import select
        result = await session.execute(select(Document).where(Document.id == document_id))
        db_doc = result.scalar_one_or_none()
        if db_doc:
            db_doc.status = "completed"
            db_doc.chunk_count = len(chunks)
            await session.commit()

    return True
