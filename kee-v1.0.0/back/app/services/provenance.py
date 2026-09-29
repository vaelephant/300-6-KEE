from uuid import uuid4
from sqlalchemy import select
from app.db.session import SessionLocal
from app.db.tables import KnowledgeVersionRow, KnowledgeRow
from app.repositories.database import to_obj


class ProvenanceService:
    def snapshot(self, obj, reason="update"):
        payload = {
            "id": obj.id,
            "content": obj.content,
            "source": obj.source,
            "type": obj.type,
            "canonical_key": obj.canonical_key,
            "entities": obj.entities,
            "relations": obj.relations,
            "evidence": [
                {
                    "id": e.id,
                    "source": e.source,
                    "excerpt": e.excerpt,
                    "source_type": e.source_type,
                }
                for e in obj.evidence
            ],
            "confidence": obj.confidence,
            "version": obj.version,
            "status": obj.status,
            "supersedes_id": obj.supersedes_id,
            "metadata": obj.metadata,
        }
        with SessionLocal() as s:
            exists = s.scalar(
                select(KnowledgeVersionRow).where(
                    KnowledgeVersionRow.knowledge_id == obj.id,
                    KnowledgeVersionRow.version == obj.version,
                )
            )
            if not exists:
                s.add(
                    KnowledgeVersionRow(
                        id=str(uuid4()),
                        knowledge_id=obj.id,
                        version=obj.version,
                        content=obj.content,
                        status=obj.status,
                        confidence=obj.confidence,
                        snapshot=payload,
                        reason=reason,
                    )
                )
                s.commit()

    def history(self, knowledge_id):
        with SessionLocal() as s:
            rows = s.scalars(
                select(KnowledgeVersionRow)
                .where(KnowledgeVersionRow.knowledge_id == knowledge_id)
                .order_by(KnowledgeVersionRow.version.desc(), KnowledgeVersionRow.created_at.desc())
            ).all()
            return [
                {
                    "version": r.version,
                    "content": r.content,
                    "status": r.status,
                    "confidence": r.confidence,
                    "reason": r.reason,
                    "created_at": r.created_at,
                    "snapshot": r.snapshot,
                }
                for r in rows
            ]

    def provenance(self, knowledge_id: str, obj=None) -> dict:
        """Evidence / lineage pack for a knowledge object."""
        if obj is None:
            with SessionLocal() as s:
                row = s.get(KnowledgeRow, knowledge_id)
                obj = to_obj(row) if row else None
        if obj is None:
            return {"knowledge_id": knowledge_id, "found": False}
        return {
            "knowledge_id": knowledge_id,
            "found": True,
            "source": obj.source,
            "evidence": [
                {
                    "id": e.id,
                    "source": e.source,
                    "excerpt": e.excerpt,
                    "source_type": e.source_type,
                }
                for e in (obj.evidence or [])
            ],
            "supersedes_id": obj.supersedes_id,
            "version": obj.version,
            "status": obj.status,
            "confidence": obj.confidence,
            "metadata": obj.metadata or {},
            "entities": obj.entities or [],
            "relations": obj.relations or [],
        }


provenance_service = ProvenanceService()
