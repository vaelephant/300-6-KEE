from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Any

from app.services import model_settings as ms
from app.services.ai_provider import ai_provider
from app.integrations.vector import vector_provider

router = APIRouter(prefix="/system/models", tags=["models"])


class ModelsUpdate(BaseModel):
    llm: dict[str, Any] | None = None
    embedding: dict[str, Any] | None = None
    reranker: dict[str, Any] | None = None


class ModelsTest(BaseModel):
    target: str = Field(..., description="llm | embedding")


class ModelsList(BaseModel):
    """List remote models from an OpenAI-compatible /models endpoint."""

    target: str = Field("llm", description="llm | embedding")
    base_url: str | None = None
    api_key: str | None = Field(
        None,
        description="Optional; blank uses saved key for that target",
    )


@router.get("")
async def get_models():
    return ms.public_view()


@router.put("")
async def put_models(body: ModelsUpdate):
    payload = body.model_dump(exclude_none=True)
    return ms.update_settings(payload)


@router.post("/test")
async def test_models(body: ModelsTest):
    if body.target == "llm":
        return await ai_provider.test_chat()
    if body.target == "embedding":
        return await vector_provider.test_embed()
    return {"ok": False, "error": "target must be llm or embedding"}


@router.post("/list")
async def list_remote_models(body: ModelsList):
    eff = ms.effective()
    if body.target == "embedding":
        base = body.base_url if body.base_url is not None else eff.embedding.base_url
        key = body.api_key if body.api_key not in (None, "") else eff.embedding.api_key
        # fall back to LLM endpoint if embedding URL empty (common: same Ollama /v1)
        if not base:
            base = eff.llm.base_url
            if body.api_key in (None, "") and not key:
                key = eff.llm.api_key
    else:
        base = body.base_url if body.base_url is not None else eff.llm.base_url
        key = body.api_key if body.api_key not in (None, "") else eff.llm.api_key

    result = await ai_provider.list_models(base_url=base or "", api_key=key or "")
    result["target"] = body.target
    return result
