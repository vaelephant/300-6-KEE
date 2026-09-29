from app.repositories.database import repository
from app.schemas.knowledge import KnowledgeCreate
from app.services.understanding import understanding_service
from app.services.audit import audit_service

class IngestionService:
    async def ingest(self, data: KnowledgeCreate):
        objects = await understanding_service.build_objects_async(data)
        stored = [await repository.add(obj) for obj in objects]
        for obj in stored: await audit_service.record("knowledge_ingested", obj.id, {"source": obj.source})
        return {"accepted": True, "count": len(stored), "knowledge": stored}

ingestion_service = IngestionService()
