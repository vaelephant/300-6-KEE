import logging
import os
import re
from pathlib import Path
from uuid import uuid4

from docx import Document
from fastapi import UploadFile, HTTPException
from pypdf import PdfReader

from app.core.config import settings
from app.db.session import SessionLocal
from app.db.tables import DocumentRow, JobRow
from app.models.knowledge import utcnow
from app.schemas.knowledge import KnowledgeCreate
from app.services.understanding import understanding_service
from app.services.evolution import evolution_service
from app.services.audit import audit_service
from app.workers.queue import enqueue_ingest

log = logging.getLogger("kee.ingest")

ALLOWED = {".txt", ".md", ".pdf", ".docx"}


def extract(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if ext == ".pdf":
        return "\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)
    if ext == ".docx":
        return "\n".join(p.text for p in Document(str(path)).paragraphs)
    return ""


def chunks(text: str, size: int = 1800, overlap: int = 180) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    out: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        out.append(text[start:end])
        if end == len(text):
            break
        start = max(start + 1, end - overlap)
    return out


def _update_job(job_id: str, **fields):
    with SessionLocal() as s:
        row = s.get(JobRow, job_id)
        if not row:
            return
        for k, v in fields.items():
            setattr(row, k, v)
        row.updated_at = utcnow()
        s.commit()


def _update_doc(document_id: str, **fields):
    with SessionLocal() as s:
        row = s.get(DocumentRow, document_id)
        if not row:
            return
        for k, v in fields.items():
            setattr(row, k, v)
        row.updated_at = utcnow()
        s.commit()


def _job_log(
    job_id: str,
    message: str,
    *,
    level: str = "info",
    phase: str | None = None,
    **patch,
):
    """Append a structured log line into job.detail.logs and optionally patch other detail keys."""
    ts = utcnow().isoformat()
    entry = {"ts": ts, "level": level, "message": message}
    if phase:
        entry["phase"] = phase

    with SessionLocal() as s:
        row = s.get(JobRow, job_id)
        if not row:
            return
        detail = dict(row.detail or {})
        logs = list(detail.get("logs") or [])
        logs.append(entry)
        # keep last 200 lines so polling payloads stay small
        detail["logs"] = logs[-200:]
        if phase:
            detail["phase"] = phase
        for k, v in patch.items():
            detail[k] = v
        row.detail = detail
        row.updated_at = utcnow()
        s.commit()

    fn = log.info if level != "error" else log.error
    if level == "warn":
        fn = log.warning
    prefix = f"[job={job_id[:8]}"
    if phase:
        prefix += f" phase={phase}"
    prefix += "]"
    fn("%s %s", prefix, message)


class DocumentService:
    async def ingest(self, file: UploadFile, domain: str = "general"):
        """Accept upload, persist file + queued rows, enqueue Redis job. Returns immediately."""
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED:
            raise HTTPException(415, "Supported: txt, md, pdf, docx")
        os.makedirs(settings.upload_dir, exist_ok=True)
        did = str(uuid4())
        job_id = str(uuid4())
        path = Path(settings.upload_dir) / f"{did}{ext}"
        data = await file.read()
        if len(data) > 20 * 1024 * 1024:
            raise HTTPException(413, "File too large (20MB max)")
        path.write_bytes(data)

        with SessionLocal() as s:
            s.add(
                DocumentRow(
                    id=did,
                    filename=file.filename or path.name,
                    path=str(path),
                    content_type=file.content_type or "",
                    status="queued",
                    domain=domain or "general",
                    job_id=job_id,
                )
            )
            s.add(
                JobRow(
                    id=job_id,
                    kind="ingest_document",
                    document_id=did,
                    status="queued",
                    detail={
                        "filename": file.filename or path.name,
                        "phase": "queued",
                        "logs": [
                            {
                                "ts": utcnow().isoformat(),
                                "level": "info",
                                "phase": "queued",
                                "message": f"已接收 {file.filename or path.name}（{len(data)} bytes），等待 worker",
                            }
                        ],
                    },
                )
            )
            s.commit()

        log.info("[job=%s] queued document=%s file=%s size=%s", job_id[:8], did[:8], file.filename, len(data))

        try:
            await enqueue_ingest(job_id, did)
            _job_log(job_id, "已写入 Redis 队列", phase="queued")
        except HTTPException:
            _job_log(job_id, "Redis 入队失败", level="error", phase="failed")
            _update_job(job_id, status="failed", error="Redis enqueue failed")
            _update_doc(did, status="failed", error="Redis enqueue failed")
            raise

        await audit_service.record(
            "document_queued",
            None,
            {"document_id": did, "job_id": job_id, "filename": file.filename},
        )
        return {
            "accepted": True,
            "status": "queued",
            "job_id": job_id,
            "document_id": did,
            "filename": file.filename,
        }

    async def process_document(self, job_id: str, document_id: str) -> dict:
        """Worker body: extract → chunk → understand → evolve."""
        with SessionLocal() as s:
            doc = s.get(DocumentRow, document_id)
            if not doc:
                _update_job(job_id, status="failed", error="document_not_found")
                _job_log(job_id, "文档不存在", level="error", phase="failed")
                return {"ok": False, "error": "document_not_found"}
            path = Path(doc.path)
            domain = doc.domain or "general"
            filename = doc.filename

        _update_job(job_id, status="running")
        _update_doc(document_id, status="processing")
        _job_log(job_id, f"Worker 开始处理 · {filename}", phase="running")

        try:
            _job_log(job_id, f"抽取文本 · {path.suffix}", phase="extract")
            text = extract(path)
            if not text.strip():
                raise ValueError("No readable text found")
            cs = chunks(text)
            _update_job(
                job_id,
                total=len(cs),
                progress=0,
            )
            _job_log(
                job_id,
                f"抽取完成 · {len(text)} 字符 → {len(cs)} 个分块",
                phase="extract",
                filename=filename,
                chars=len(text),
                chunks=len(cs),
            )

            claim_count = 0
            conflict_count = 0
            for i, c in enumerate(cs):
                _job_log(
                    job_id,
                    f"理解分块 {i + 1}/{len(cs)}（{len(c)} 字符）",
                    phase="understand",
                )
                objs = await understanding_service.build_objects_async(
                    KnowledgeCreate(
                        content=c,
                        source=filename or "upload",
                        domain=domain,
                        metadata={"document_id": document_id, "chunk_index": i},
                    )
                )
                _job_log(
                    job_id,
                    f"分块 {i + 1} 抽出 {len(objs)} 条候选",
                    phase="understand",
                    claims=claim_count,
                )
                for obj in objs[:30]:
                    result = await evolution_service.evolve(obj)
                    claim_count += 1
                    decision = result.get("decision", "?")
                    if decision == "review_required":
                        conflict_count += 1
                    if claim_count <= 3 or claim_count % 5 == 0 or decision == "review_required":
                        _job_log(
                            job_id,
                            f"演化 #{claim_count} → {decision}",
                            phase="evolve",
                            claims=claim_count,
                            conflicts=conflict_count,
                        )
                _update_job(
                    job_id,
                    progress=i + 1,
                )
                _job_log(
                    job_id,
                    f"分块 {i + 1}/{len(cs)} 完成 · 累计 claims={claim_count}",
                    phase="evolve",
                    claims=claim_count,
                    conflicts=conflict_count,
                )

            _update_doc(
                document_id,
                status="done",
                chunks=len(cs),
                claims=claim_count,
                error=None,
            )
            _update_job(
                job_id,
                status="done",
                progress=len(cs),
                total=len(cs),
                error=None,
            )
            _job_log(
                job_id,
                f"完成 · chunks={len(cs)} claims={claim_count} conflicts={conflict_count}",
                level="info",
                phase="done",
                filename=filename,
                chunks=len(cs),
                claims=claim_count,
                conflicts=conflict_count,
            )
            await audit_service.record(
                "document_ingested",
                None,
                {
                    "document_id": document_id,
                    "job_id": job_id,
                    "filename": filename,
                    "chunks": len(cs),
                    "claims": claim_count,
                    "conflicts": conflict_count,
                },
            )
            return {
                "ok": True,
                "chunks": len(cs),
                "claims": claim_count,
                "conflicts": conflict_count,
            }
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            _update_job(job_id, status="failed", error=err)
            _update_doc(document_id, status="failed", error=err)
            _job_log(job_id, f"失败 · {err}", level="error", phase="failed")
            await audit_service.record(
                "document_ingest_failed",
                None,
                {"document_id": document_id, "job_id": job_id, "error": err},
            )
            return {"ok": False, "error": err}


document_service = DocumentService()
