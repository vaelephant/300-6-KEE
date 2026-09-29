"""Job row lifecycle — process_document without Redis."""
import asyncio
from pathlib import Path
from uuid import uuid4

from app.db.session import init_db, SessionLocal
from app.db.tables import DocumentRow, JobRow
from app.services.documents import document_service


def test_process_document_updates_job_and_doc(tmp_path):
    init_db()
    did = str(uuid4())
    job_id = str(uuid4())
    path = tmp_path / f"{did}.txt"
    path.write_text("Water boils at 100C. Ice melts at 0C.", encoding="utf-8")

    with SessionLocal() as s:
        s.add(
            DocumentRow(
                id=did,
                filename="water.txt",
                path=str(path),
                content_type="text/plain",
                status="queued",
                domain="general",
                job_id=job_id,
            )
        )
        s.add(
            JobRow(
                id=job_id,
                kind="ingest_document",
                document_id=did,
                status="queued",
                detail={"filename": "water.txt"},
            )
        )
        s.commit()

    result = asyncio.run(document_service.process_document(job_id, did))
    assert result.get("ok") is True, result
    assert result["claims"] >= 1

    with SessionLocal() as s:
        job = s.get(JobRow, job_id)
        doc = s.get(DocumentRow, did)
        assert job is not None and job.status == "done"
        assert doc is not None and doc.status == "done"
        assert doc.claims >= 1
        logs = (job.detail or {}).get("logs") or []
        assert len(logs) >= 3
        phases = {x.get("phase") for x in logs}
        assert "extract" in phases or "evolve" in phases or "done" in phases
        assert any("完成" in (x.get("message") or "") for x in logs)
