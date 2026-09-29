"""Redis / arq queue helpers. Fail loud when Redis is down — no silent sync fallback."""
from __future__ import annotations

from urllib.parse import urlparse

from arq import create_pool
from arq.connections import RedisSettings, ArqRedis
from fastapi import HTTPException

from app.core.config import settings

_pool: ArqRedis | None = None


def redis_settings() -> RedisSettings:
    url = (settings.redis_url or "").strip()
    if not url:
        raise ValueError("REDIS_URL not configured")
    u = urlparse(url)
    return RedisSettings(
        host=u.hostname or "localhost",
        port=u.port or 6379,
        database=int((u.path or "/0").lstrip("/") or "0"),
        password=u.password,
        username=u.username,
    )


async def get_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        try:
            _pool = await create_pool(redis_settings())
        except Exception as e:
            raise HTTPException(503, f"Redis queue unavailable: {type(e).__name__}: {e}") from e
    return _pool


async def enqueue_ingest(job_id: str, document_id: str) -> str:
    try:
        pool = await get_pool()
        await pool.enqueue_job("ingest_document", job_id, document_id, _job_id=job_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"Failed to enqueue: {type(e).__name__}: {e}") from e
    return job_id
