from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.runtime import runtime_service

router = APIRouter(prefix="/runtime", tags=["runtime"])


class ContextRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=6, ge=1, le=20)
    domain: str | None = None
    min_trust: float = Field(default=0.45, ge=0, le=1)
    include_guarded: bool = True


@router.post("/context")
async def context(payload: ContextRequest):
    return await runtime_service.context(**payload.model_dump(), source="api")


@router.post("/agent")
async def agent_context(payload: ContextRequest):
    return await runtime_service.agent_pack(**payload.model_dump(), source="api")
