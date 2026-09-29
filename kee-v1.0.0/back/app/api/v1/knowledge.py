from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.schemas.knowledge import KnowledgeCreate, QueryRequest, FeedbackRequest, EvolveRequest
from app.services.ingestion import ingestion_service
from app.services.retrieval import retrieval_service
from app.services.evolution import evolution_service
from app.services.understanding import understanding_service

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

@router.post("/ingest")
async def ingest(payload: KnowledgeCreate):
    return await ingestion_service.ingest(payload)

@router.post("/query")
async def query(payload: QueryRequest):
    results = await retrieval_service.query(payload.question, payload.top_k, payload.domain, payload.include_superseded)
    return {"question": payload.question, "domain": payload.domain, "results": results}

@router.post("/feedback")
async def feedback(payload: FeedbackRequest):
    result = await evolution_service.feedback(payload.knowledge_id, payload.rating, payload.correction, payload.source)
    if not result.get("accepted"): raise HTTPException(404, result.get("reason"))
    return result

@router.post("/evolve")
async def evolve(payload: EvolveRequest):
    objs = await understanding_service.build_objects_async(KnowledgeCreate(**payload.model_dump(exclude={"auto_promote"})))
    results = [await evolution_service.evolve(x, payload.auto_promote) for x in objs]
    return {"accepted": True, "count": len(results), "results": results}

class ReviewRequest(BaseModel):
    action: str

@router.post("/{knowledge_id}/review")
async def review(knowledge_id: str, payload: ReviewRequest):
    result = await evolution_service.review(knowledge_id, payload.action)
    if not result.get("accepted"): raise HTTPException(400 if result.get("reason") == "invalid_action" else 404, result.get("reason"))
    return result

@router.get("/{knowledge_id}")
async def detail(knowledge_id: str):
    from app.repositories.database import repository
    from app.services.provenance import provenance_service
    obj=await repository.get(knowledge_id)
    if not obj: raise HTTPException(404,"knowledge_not_found")
    from app.services.trust import trust_service
    return {
        "knowledge": obj,
        "history": provenance_service.history(knowledge_id),
        "provenance": provenance_service.provenance(knowledge_id, obj),
        "trust": trust_service.evaluate(obj),
    }
