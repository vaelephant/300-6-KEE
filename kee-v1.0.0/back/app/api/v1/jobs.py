from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.tables import JobRow

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _job_dict(r: JobRow) -> dict:
    detail = r.detail or {}
    return {
        "id": r.id,
        "kind": r.kind,
        "document_id": r.document_id,
        "status": r.status,
        "progress": r.progress,
        "total": r.total,
        "phase": detail.get("phase"),
        "logs": list(detail.get("logs") or []),
        "detail": detail,
        "error": r.error,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


@router.get("/")
async def list_jobs(document_id: str | None = Query(None), limit: int = Query(50, ge=1, le=200)):
    with SessionLocal() as s:
        q = select(JobRow).order_by(JobRow.created_at.desc()).limit(limit)
        if document_id:
            q = (
                select(JobRow)
                .where(JobRow.document_id == document_id)
                .order_by(JobRow.created_at.desc())
                .limit(limit)
            )
        rows = s.scalars(q).all()
        return {"items": [_job_dict(r) for r in rows], "count": len(rows)}


@router.get("/{job_id}")
async def get_job(job_id: str):
    with SessionLocal() as s:
        row = s.get(JobRow, job_id)
        if not row:
            raise HTTPException(404, "job_not_found")
        return _job_dict(row)
