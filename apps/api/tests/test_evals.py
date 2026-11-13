"""Golden retrieval evals.

These run against the SQLite fallback in tests; production uses Postgres FTS.
They keep the retrieval contract and ranking behavior stable across changes.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Document, DocumentChunk, Workspace
from app.services.retrieval import retrieval_service

CORPUS: dict[str, list[str]] = {
    "security.md": [
        "Rotate API keys every ninety days and audit access.",
        "Never commit secrets to the repository.",
    ],
    "rag.md": [
        "Postgres full-text search ranks document chunks.",
        "Qdrant provides optional semantic retrieval.",
    ],
    "deploy.md": [
        "Run alembic upgrade head before starting the API.",
    ],
}


async def _seed(db_session: AsyncSession) -> Workspace:
    workspace = Workspace(id=uuid.uuid4(), name="Eval Workspace")
    db_session.add(workspace)
    await db_session.commit()

    for filename, chunks in CORPUS.items():
        document = Document(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            filename=filename,
            document_type="markdown",
            size_bytes=100,
            chunk_count=len(chunks),
            status="completed",
        )
        db_session.add(document)
        await db_session.commit()

        for ordinal, content in enumerate(chunks):
            db_session.add(
                DocumentChunk(
                    id=uuid.uuid4(),
                    document_id=document.id,
                    workspace_id=workspace.id,
                    ordinal=ordinal,
                    content=content,
                )
            )
        await db_session.commit()

    return workspace


async def test_retrieval_golden_set(db_session: AsyncSession) -> None:
    workspace = await _seed(db_session)

    cases = [
        ("Rotate API keys", "security.md"),
        ("full-text search ranks", "rag.md"),
        ("alembic upgrade head", "deploy.md"),
    ]

    for query, expected in cases:
        results = await retrieval_service.search(
            query, workspace.id, db_session, limit=1
        )
        assert results, f"no result for {query!r}"
        assert results[0].filename == expected


async def test_retrieval_returns_no_match(db_session: AsyncSession) -> None:
    workspace = await _seed(db_session)

    results = await retrieval_service.search(
        "quantum chromodynamics", workspace.id, db_session
    )

    assert results == []
