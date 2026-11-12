"""Tests for the Postgres-backed job queue and worker dispatch."""

from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Job
from app.services.job_service import job_service, utcnow
from app.tasks import worker


async def test_enqueue_and_claim(db_session: AsyncSession) -> None:
    job = await job_service.enqueue(db_session, kind="test", payload={"a": 1})
    assert job.status == "pending"
    assert job.attempts == 0

    claimed = await job_service.claim_next(db_session, "worker-1")

    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.status == "running"
    assert claimed.attempts == 1
    assert claimed.locked_by == "worker-1"

    assert await job_service.claim_next(db_session, "worker-2") is None


async def test_claim_respects_run_at(db_session: AsyncSession) -> None:
    await job_service.enqueue(
        db_session,
        kind="test",
        payload={},
        run_at=utcnow() + timedelta(hours=1),
    )

    assert await job_service.claim_next(db_session, "worker-1") is None


async def test_mark_completed(db_session: AsyncSession) -> None:
    job = await job_service.enqueue(db_session, kind="test", payload={})
    claimed = await job_service.claim_next(db_session, "worker-1")
    assert claimed is not None

    await job_service.mark_completed(db_session, claimed)

    refreshed = await db_session.get(Job, job.id)
    assert refreshed is not None
    assert refreshed.status == "completed"
    assert refreshed.locked_by is None


async def test_mark_failed_marks_failed_after_max_attempts(
    db_session: AsyncSession,
) -> None:
    job = await job_service.enqueue(db_session, kind="test", payload={}, max_attempts=1)
    claimed = await job_service.claim_next(db_session, "worker-1")
    assert claimed is not None

    await job_service.mark_failed(db_session, claimed, "boom")

    refreshed = await db_session.get(Job, job.id)
    assert refreshed is not None
    assert refreshed.status == "failed"
    assert refreshed.last_error == "boom"


async def test_mark_failed_requeues_below_max_attempts(
    db_session: AsyncSession,
) -> None:
    job = await job_service.enqueue(db_session, kind="test", payload={}, max_attempts=2)
    claimed = await job_service.claim_next(db_session, "worker-1")
    assert claimed is not None

    await job_service.mark_failed(db_session, claimed, "boom")

    refreshed = await db_session.get(Job, job.id)
    assert refreshed is not None
    assert refreshed.status == "pending"


async def test_worker_dispatches_and_completes(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    called: list[dict[str, object]] = []

    async def handler(db: AsyncSession, payload: dict[str, object]) -> None:
        called.append(payload)

    monkeypatch.setitem(worker.HANDLERS, "test.noop", handler)
    await job_service.enqueue(db_session, kind="test.noop", payload={"ok": True})

    worked = await worker.process_next_job(db_session, "worker-1")

    assert worked is True
    assert called == [{"ok": True}]
    jobs = (await db_session.execute(select(Job))).scalars().all()
    assert jobs[0].status == "completed"


async def test_worker_marks_failures(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def handler(db: AsyncSession, payload: dict[str, object]) -> None:
        raise RuntimeError("handler failed")

    monkeypatch.setitem(worker.HANDLERS, "test.fail", handler)
    job = await job_service.enqueue(
        db_session, kind="test.fail", payload={}, max_attempts=1
    )

    worked = await worker.process_next_job(db_session, "worker-1")

    assert worked is True
    refreshed = await db_session.get(Job, job.id)
    assert refreshed is not None
    assert refreshed.status == "failed"
    assert refreshed.last_error == "handler failed"


async def test_unknown_job_kind_fails(
    db_session: AsyncSession,
) -> None:
    job = await job_service.enqueue(
        db_session, kind="missing.kind", payload={}, max_attempts=1
    )

    worked = await worker.process_next_job(db_session, "worker-1")

    assert worked is True
    refreshed = await db_session.get(Job, job.id)
    assert refreshed is not None
    assert refreshed.status == "failed"
    assert "Unknown job kind" in (refreshed.last_error or "")
