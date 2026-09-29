"""MCP pack fetch — in-process RuntimeService (default) or remote HTTP."""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.config import settings

_mcp_db_ready = False


def _mcp_ensure_db() -> None:
    global _mcp_db_ready
    if _mcp_db_ready:
        return
    from app.db.session import init_db

    init_db()
    _mcp_db_ready = True


async def mcp_fetch_pack(
    question: str,
    top_k: int = 6,
    min_trust: float = 0.45,
    domain: str | None = None,
    include_guarded: bool = True,
) -> dict[str, Any]:
    """Return {protocol, instructions, context_pack} for MCP tool responses."""
    base = (settings.kee_api_base or "").rstrip("/")
    kwargs = {
        "question": question,
        "top_k": top_k,
        "min_trust": min_trust,
        "domain": domain,
        "include_guarded": include_guarded,
    }
    if base:
        return await _mcp_remote_pack(base, **kwargs)
    return await _mcp_local_pack(**kwargs)


async def _mcp_local_pack(**kwargs: Any) -> dict[str, Any]:
    _mcp_ensure_db()
    from app.services.runtime import runtime_service

    return await runtime_service.agent_pack(**kwargs, source="mcp")


async def _mcp_remote_pack(base: str, **kwargs: Any) -> dict[str, Any]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if settings.kee_api_key:
        headers["Authorization"] = f"Bearer {settings.kee_api_key}"
    url = f"{base}/api/v1/runtime/agent"
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(url, json=kwargs, headers=headers)
        r.raise_for_status()
        return r.json()


def mcp_pack_text(pack: dict[str, Any]) -> str:
    return json.dumps(pack, ensure_ascii=False, indent=2, default=str)
