from uuid import uuid4
from sqlalchemy import select
from app.db.session import SessionLocal
from app.db.tables import EventRow
class AuditService:
 async def record(self,event_type,knowledge_id=None,detail=None):
  e=EventRow(id=str(uuid4()),event_type=event_type,knowledge_id=knowledge_id,detail=detail or {})
  with SessionLocal() as s: s.add(e); s.commit(); s.refresh(e)
  return {"id":e.id,"event_type":e.event_type,"knowledge_id":e.knowledge_id,"detail":e.detail,"created_at":e.created_at.isoformat()}
 async def list(self,limit=50):
  with SessionLocal() as s:
   rows=s.scalars(select(EventRow).order_by(EventRow.created_at.desc()).limit(limit)).all(); return [{"id":e.id,"event_type":e.event_type,"knowledge_id":e.knowledge_id,"detail":e.detail or {},"created_at":e.created_at.isoformat()} for e in rows]
audit_service=AuditService()
