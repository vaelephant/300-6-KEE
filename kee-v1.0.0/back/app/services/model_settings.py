"""Runtime model settings overlay on top of env Defaults.

Persisted to data/model_settings.json. Secrets masked on read.
"""
from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import settings

_LOCK = Lock()
_OVERLAY_PATH = Path("data/model_settings.json")
_overlay: dict[str, Any] = {}


class LlmConfig(BaseModel):
    base_url: str = ""
    api_key: str = ""
    model: str = ""


class EmbeddingConfig(BaseModel):
    provider: str = "local"  # local | bge | openai_compatible
    model: str = "BAAI/bge-m3"
    base_url: str = ""
    api_key: str = ""


class RerankerConfig(BaseModel):
    model: str = "BAAI/bge-reranker-v2-m3"


class ModelSettings(BaseModel):
    llm: LlmConfig = Field(default_factory=LlmConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    reranker: RerankerConfig = Field(default_factory=RerankerConfig)


def _mask(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 4:
        return "****"
    return key[:2] + "****" + key[-2:]


def _defaults() -> ModelSettings:
    return ModelSettings(
        llm=LlmConfig(
            base_url=settings.llm_base_url or "",
            api_key=settings.llm_api_key or "",
            model=settings.llm_model or "",
        ),
        embedding=EmbeddingConfig(
            provider=settings.embedding_provider or "local",
            model=settings.embedding_model or "BAAI/bge-m3",
            base_url=getattr(settings, "embedding_base_url", "") or "",
            api_key=getattr(settings, "embedding_api_key", "") or "",
        ),
        reranker=RerankerConfig(model=settings.reranker_model or "BAAI/bge-reranker-v2-m3"),
    )


def load_overlay() -> None:
    global _overlay
    with _LOCK:
        if _OVERLAY_PATH.exists():
            try:
                _overlay = json.loads(_OVERLAY_PATH.read_text(encoding="utf-8"))
            except Exception:
                _overlay = {}
        else:
            _overlay = {}


def _save_overlay(data: dict[str, Any]) -> None:
    global _overlay
    _OVERLAY_PATH.parent.mkdir(parents=True, exist_ok=True)
    _OVERLAY_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    _overlay = data


def effective() -> ModelSettings:
    base = _defaults().model_dump()
    with _LOCK:
        ov = dict(_overlay)
    for section in ("llm", "embedding", "reranker"):
        if section in ov and isinstance(ov[section], dict):
            base[section] = {**base[section], **{k: v for k, v in ov[section].items() if v is not None}}
    return ModelSettings.model_validate(base)


def public_view() -> dict[str, Any]:
    m = effective()
    d = m.model_dump()
    d["llm"]["api_key"] = _mask(d["llm"].get("api_key") or "")
    d["llm"]["api_key_set"] = bool(m.llm.api_key)
    d["embedding"]["api_key"] = _mask(d["embedding"].get("api_key") or "")
    d["embedding"]["api_key_set"] = bool(m.embedding.api_key)
    return d


def update_settings(payload: dict[str, Any]) -> dict[str, Any]:
    """Merge partial update. Empty api_key string means keep existing."""
    current = effective().model_dump()
    with _LOCK:
        ov = dict(_overlay)

    for section in ("llm", "embedding", "reranker"):
        if section not in payload or not isinstance(payload[section], dict):
            continue
        patch = dict(payload[section])
        if "api_key" in patch and (patch["api_key"] is None or patch["api_key"] == ""):
            # keep previous effective key
            patch.pop("api_key")
            if section in ov and "api_key" in ov[section]:
                pass  # keep overlay key
            elif current[section].get("api_key"):
                # ensure overlay keeps env key if we're clearing intentionally — no, keep env via not writing
                pass
        section_ov = dict(ov.get(section) or {})
        section_ov.update({k: v for k, v in patch.items() if v is not None})
        ov[section] = section_ov

    _save_overlay(ov)
    return public_view()


# Load once on import
load_overlay()
