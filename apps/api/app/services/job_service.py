"""
AI Workspace API — Job Service

Durable Postgres job queue using FOR UPDATE SKIP LOCKED.
"""

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Job


def utcnow() -> datetime:
    """Return a naive UTC timestamp, matching the database column type."""
    return datetime.now(UTC).replace(tzinfo=None)


class JobService:
    """Enqueue, claim, and finalize background jobs."""

    async def enqueue(
        self,
        db: AsyncSession,
        *,
        kind: str,
        payload: dict[str, Any],
        max_attempts: int = 3,
        run_at: datetime | None = None,
    ) -> Job:
        job = Job(
            kind=kind,
            payload=json.dumps(payload),
            status="pending",
            max_attempts=max_attempts,
            run_at=run_at or utcnow(),
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job

    async def claim_next(self, db: AsyncSession, worker_id: str) -> Job | None:
        result = await db.execute(
            select(Job)
            .where(Job.status == "pending", Job.run_at <= utcnow())
            .order_by(Job.run_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        job = result.scalar_one_or_none()
        if job is None:
            return None

        job.status = "running"
        job.attempts += 1
        job.locked_at = utcnow()
        job.locked_by = worker_id
        await db.commit()
        await db.refresh(job)
        return job

    async def mark_completed(self, db: AsyncSession, job: Job) -> None:
        job.status = "completed"
        job.locked_at = None
        job.locked_by = None
        await db.commit()

    async def mark_failed(self, db: AsyncSession, job: Job, error: str) -> None:
        job.last_error = error[:2000]
        job.locked_at = None
        job.locked_by = None
        job.status = "failed" if job.attempts >= job.max_attempts else "pending"
        await db.commit()


job_service = JobService()
