from sqlalchemy import select, func
from app.db.session import SessionLocal
from app.db.tables import KnowledgeRow, EventRow, DocumentRow
from app.models.knowledge import KnowledgeObject, Evidence, utcnow

def to_obj(r):
 return KnowledgeObject(id=r.id,content=r.content,source=r.source,type=r.type,canonical_key=r.canonical_key,entities=r.entities or [],relations=r.relations or [],evidence=[Evidence(**{k:v for k,v in e.items() if k in {"id","source","excerpt","source_type"}}) for e in (r.evidence or [])],confidence=r.confidence,version=r.version,status=r.status,supersedes_id=r.supersedes_id,metadata=r.meta or {},created_at=r.created_at,updated_at=r.updated_at)
class DatabaseRepository:
 async def add(self,o): return await self.save(o)
 async def save(self,o):
  with SessionLocal() as s:
   r=s.get(KnowledgeRow,o.id); data=dict(content=o.content,source=o.source,type=o.type,canonical_key=o.canonical_key,entities=o.entities,relations=o.relations,evidence=[{"id":e.id,"source":e.source,"excerpt":e.excerpt,"source_type":e.source_type} for e in o.evidence],confidence=o.confidence,version=o.version,status=o.status,supersedes_id=o.supersedes_id,meta=o.metadata,updated_at=utcnow())
   if r:
    for k,v in data.items(): setattr(r,k,v)
   else: s.add(KnowledgeRow(id=o.id,created_at=o.created_at,**data))
   s.commit()
  from app.services.provenance import provenance_service
  provenance_service.snapshot(o, "persist")
  try:
   from app.integrations.graph_store import graph_store
   graph_store.sync(o)
  except Exception:
   pass
  return o
 async def get(self,id):
  with SessionLocal() as s:
   r=s.get(KnowledgeRow,id); return to_obj(r) if r else None
 async def list(self,limit=1000):
  with SessionLocal() as s: return [to_obj(r) for r in s.scalars(select(KnowledgeRow).order_by(KnowledgeRow.updated_at.desc()).limit(limit)).all()]
 async def stats(self):
  with SessionLocal() as s:
   return {"total":s.scalar(select(func.count()).select_from(KnowledgeRow)) or 0,"active":s.scalar(select(func.count()).select_from(KnowledgeRow).where(KnowledgeRow.status=="active")) or 0,"review_required":s.scalar(select(func.count()).select_from(KnowledgeRow).where(KnowledgeRow.status=="review_required")) or 0,"events":s.scalar(select(func.count()).select_from(EventRow)) or 0,"documents":s.scalar(select(func.count()).select_from(DocumentRow)) or 0}
repository=DatabaseRepository()
