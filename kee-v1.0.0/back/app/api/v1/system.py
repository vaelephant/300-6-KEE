from fastapi import APIRouter, Query
from sqlalchemy import select, func
from app.repositories.database import repository
from app.services.audit import audit_service
from app.services import model_settings as ms
from app.db.session import SessionLocal
from app.db.tables import DocumentRow

router = APIRouter(tags=["system"])


@router.get("/knowledge")
async def list_knowledge(limit: int = Query(50, ge=1, le=200)):
    items = await repository.list(limit)
    return {"items": [x.to_dict() for x in items], "count": len(items)}


@router.get("/events")
async def events(limit: int = Query(50, ge=1, le=200)):
    items = await audit_service.list(limit)
    return {"items": items, "count": len(items)}


@router.get("/system/stats")
async def stats():
    return await repository.stats()


@router.get("/documents")
async def documents(limit: int = Query(50, ge=1, le=200)):
    with SessionLocal() as s:
        rows = s.scalars(select(DocumentRow).order_by(DocumentRow.created_at.desc()).limit(limit)).all()
        return {
            "items": [
                {
                    "id": r.id,
                    "filename": r.filename,
                    "content_type": r.content_type,
                    "status": r.status,
                    "chunks": r.chunks,
                    "claims": r.claims,
                    "job_id": r.job_id,
                    "error": r.error,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
        }


@router.get("/system/assets")
async def assets(limit: int = Query(8, ge=1, le=40)):
    """Workbench aggregate: store / vector / files for the engine console."""
    base = await repository.stats()
    knowledge = await repository.list(limit)
    emb = ms.effective().embedding

    with SessionLocal() as s:
        docs = s.scalars(select(DocumentRow).order_by(DocumentRow.created_at.desc()).limit(limit)).all()
        doc_total = s.scalar(select(func.count()).select_from(DocumentRow)) or 0
        doc_done = (
            s.scalar(select(func.count()).select_from(DocumentRow).where(DocumentRow.status == "done")) or 0
        )
        doc_failed = (
            s.scalar(select(func.count()).select_from(DocumentRow).where(DocumentRow.status == "failed")) or 0
        )
        doc_busy = (
            s.scalar(
                select(func.count())
                .select_from(DocumentRow)
                .where(DocumentRow.status.in_(["queued", "processing"]))
            )
            or 0
        )

    # Vectors are computed on query today — indexable ≈ active knowledge in store.
    indexable = int(base.get("active") or 0)

    return {
        "store": {
            "total": base.get("total", 0),
            "active": base.get("active", 0),
            "review_required": base.get("review_required", 0),
            "events": base.get("events", 0),
            "items": [
                {
                    "id": k.id,
                    "content": k.content,
                    "source": k.source,
                    "status": k.status,
                    "confidence": k.confidence,
                    "version": k.version,
                }
                for k in knowledge
            ],
        },
        "vector": {
            "provider": emb.provider,
            "model": emb.model,
            "base_url": emb.base_url or None,
            "indexable": indexable,
            "mode": "on_query",
            "note": "向量按查询即时计算，规模对齐生效知识条数",
        },
        "files": {
            "total": doc_total,
            "done": doc_done,
            "failed": doc_failed,
            "busy": doc_busy,
            "items": [
                {
                    "id": r.id,
                    "filename": r.filename,
                    "content_type": r.content_type,
                    "status": r.status,
                    "chunks": r.chunks,
                    "claims": r.claims,
                    "job_id": r.job_id,
                    "error": r.error,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in docs
            ],
        },
        "summary": {
            "knowledge": base.get("total", 0),
            "active": base.get("active", 0),
            "review_required": base.get("review_required", 0),
            "documents": doc_total,
            "vector_indexable": indexable,
            "embedding_provider": emb.provider,
        },
    }
