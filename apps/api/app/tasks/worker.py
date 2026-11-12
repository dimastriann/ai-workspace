"""
AI Workspace API — Background Worker

Claims jobs from the Postgres queue and dispatches them to handlers.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import socket
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import async_session
from app.services.job_service import job_service
from app.tasks.ingestion import process_document

logger = logging.getLogger(__name__)

Handler = Callable[[AsyncSession, dict[str, Any]], Awaitable[None]]

HANDLERS: dict[str, Handler] = {
    "document.ingest": process_document,
}


async def process_next_job(db: AsyncSession, worker_id: str) -> bool:
    """Claim and run a single job. Returns whether a job was claimed."""
    job = await job_service.claim_next(db, worker_id)
    if job is None:
        return False

    handler = HANDLERS.get(job.kind)
    try:
        if handler is None:
            raise ValueError(f"Unknown job kind: {job.kind}")
        await handler(db, json.loads(job.payload))
        await job_service.mark_completed(db, job)
    except Exception as exc:
        logger.exception("Job %s failed", job.id)
        await job_service.mark_failed(db, job, str(exc))
    return True


async def run_once(
    worker_id: str,
    session_factory: async_sessionmaker[AsyncSession] = async_session,
) -> bool:
    """Open a fresh session and process at most one job."""
    async with session_factory() as db:
        return await process_next_job(db, worker_id)


async def worker_loop(poll_interval: float = 1.0) -> None:
    """Poll the queue until interrupted."""
    worker_id = f"{socket.gethostname()}:{os.getpid()}"
    stop = asyncio.Event()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass

    logger.info("Worker %s started", worker_id)
    while not stop.is_set():
        try:
            worked = await run_once(worker_id)
        except Exception:
            logger.exception("Worker loop error")
            worked = False

        if not worked:
            try:
                await asyncio.wait_for(stop.wait(), timeout=poll_interval)
            except TimeoutError:
                pass

    logger.info("Worker %s stopped", worker_id)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(worker_loop())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
