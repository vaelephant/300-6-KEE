from fastapi import APIRouter, HTTPException, Query
from app.repositories.database import repository
from app.services.trust import trust_service

router = APIRouter(prefix="/trust", tags=["trust"])

@router.get("/{knowledge_id}")
async def trust_detail(knowledge_id: str):
    obj = await repository.get(knowledge_id)
    if not obj: raise HTTPException(404, "knowledge_not_found")
    return {"knowledge": obj, **trust_service.evaluate(obj)}

@router.get("")
async def trust_index(limit: int = Query(50, ge=1, le=200)):
    items = await repository.list(limit)
    scored = [{"knowledge": x, **trust_service.evaluate(x)} for x in items]
    scored.sort(key=lambda x: x["trust_score"], reverse=True)
    avg = round(sum(x["trust_score"] for x in scored) / len(scored), 4) if scored else 0
    guarded = sum(1 for x in scored if x["trust_level"] in {"guarded", "low"})
    return {"average_trust": avg, "guarded_or_low": guarded, "count": len(scored), "items": scored}
