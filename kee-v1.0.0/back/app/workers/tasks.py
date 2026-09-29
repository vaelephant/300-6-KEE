"""arq worker entry: `arq app.workers.tasks.WorkerSettings`"""
from __future__ import annotations

import logging

from app.db.session import init_db
from app.workers.queue import redis_settings


async def ingest_document(ctx, job_id: str, document_id: str):
    from app.services.documents import document_service

    logging.getLogger("kee.ingest").info(
        "worker picked up job=%s document=%s", job_id[:8], document_id[:8]
    )
    return await document_service.process_document(job_id, document_id)


async def on_startup(ctx):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )
    init_db()
    logging.getLogger("kee.ingest").info("worker ready")


class WorkerSettings:
    functions = [ingest_document]
    redis_settings = redis_settings()
    on_startup = on_startup
    max_jobs = 2
    job_timeout = 3600
