from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from app.db.session import SessionLocal
from app.db.tables import KnowledgeRow, EventRow
from app.repositories.database import repository, to_obj
from app.services.provenance import provenance_service

router=APIRouter(tags=["operations"])

@router.get('/reviews')
async def reviews(limit:int=50):
    with SessionLocal() as s:
        rows=s.scalars(select(KnowledgeRow).where(KnowledgeRow.status=='review_required').order_by(KnowledgeRow.updated_at.desc()).limit(limit)).all()
        return {"items":[to_obj(r) for r in rows],"count":len(rows)}

@router.get('/knowledge/{knowledge_id}/history')
async def history(knowledge_id:str):
    obj=await repository.get(knowledge_id)
    if not obj: raise HTTPException(404,'knowledge_not_found')
    return {"knowledge_id":knowledge_id,"current":obj,"versions":provenance_service.history(knowledge_id)}

@router.get('/knowledge/{knowledge_id}/provenance')
async def provenance(knowledge_id:str):
    obj=await repository.get(knowledge_id)
    if not obj: raise HTTPException(404,'knowledge_not_found')
    return {"knowledge_id":knowledge_id,"source":obj.source,"evidence":obj.evidence,"supersedes_id":obj.supersedes_id,"version":obj.version,"status":obj.status,"confidence":obj.confidence,"metadata":obj.metadata}

@router.get('/runtime/readiness')
async def readiness():
    import time
    from datetime import datetime, timezone
    from urllib.parse import urlparse
    from app.core.config import settings
    from sqlalchemy import text

    def mask_url(url: str) -> str:
        if not url:
            return ""
        try:
            u = urlparse(url.replace("postgresql+psycopg://", "postgresql://").replace("sqlite+pysqlite://", "sqlite://"))
            host = u.hostname or "local"
            port = f":{u.port}" if u.port else ""
            path = u.path or ""
            return f"{u.scheme}://{host}{port}{path}"
        except Exception:
            return "configured"

    links = []

    # API process itself
    links.append({
        "id": "api",
        "name": "KEE API",
        "role": "runtime",
        "status": "connected",
        "latency_ms": 0,
        "target": "in-process",
        "detail": settings.app_name,
    })

    # Database
    t0 = time.perf_counter()
    db_status, db_detail = "error", ""
    try:
        with SessionLocal() as s:
            s.execute(text("SELECT 1"))
        db_status = "postgres" if "postgres" in settings.database_url else "sqlite"
        db_detail = "query ok"
    except Exception as e:
        db_status = "error"
        db_detail = type(e).__name__
    links.append({
        "id": "database",
        "name": "Database",
        "role": "store",
        "status": "connected" if db_status in {"postgres", "sqlite"} else "error",
        "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        "target": mask_url(settings.database_url),
        "detail": db_status if db_status in {"postgres", "sqlite"} else db_detail,
        "engine": db_status if db_status in {"postgres", "sqlite"} else None,
    })

    # Neo4j
    neo_status, neo_detail = "optional", "sync disabled"
    neo_ms = None
    if settings.enable_neo4j_sync and settings.neo4j_uri:
        t0 = time.perf_counter()
        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
            driver.verify_connectivity()
            driver.close()
            neo_status, neo_detail = "connected", "bolt ok"
        except Exception as e:
            neo_status, neo_detail = "error", type(e).__name__
        neo_ms = round((time.perf_counter() - t0) * 1000, 1)
    links.append({
        "id": "neo4j",
        "name": "Neo4j Graph",
        "role": "graph",
        "status": neo_status,
        "latency_ms": neo_ms,
        "target": mask_url(settings.neo4j_uri) if settings.neo4j_uri else "",
        "detail": neo_detail,
        "enabled": bool(settings.enable_neo4j_sync and settings.neo4j_uri),
    })

    # Redis
    redis_status, redis_detail = "optional", "not configured"
    redis_ms = None
    if settings.redis_url:
        t0 = time.perf_counter()
        try:
            import redis as redis_lib
            r = redis_lib.from_url(settings.redis_url, socket_connect_timeout=1)
            redis_status = "connected" if r.ping() else "error"
            redis_detail = "PING" if redis_status == "connected" else "ping failed"
        except Exception as e:
            redis_status, redis_detail = "error", type(e).__name__
        redis_ms = round((time.perf_counter() - t0) * 1000, 1)
    links.append({
        "id": "redis",
        "name": "Redis Queue",
        "role": "cache",
        "status": redis_status,
        "latency_ms": redis_ms,
        "target": mask_url(settings.redis_url) if settings.redis_url else "",
        "detail": "arq job queue" if redis_status == "connected" else redis_detail,
        "wired": redis_status == "connected",
    })

    # LLM — use effective overlay
    from app.services import model_settings as ms
    eff = ms.effective()
    llm_configured = bool(eff.llm.api_key and eff.llm.model and eff.llm.base_url)
    links.append({
        "id": "llm",
        "name": "LLM Provider",
        "role": "ai",
        "status": "configured" if llm_configured else "fallback",
        "latency_ms": None,
        "target": mask_url(eff.llm.base_url) if eff.llm.base_url else "local-rules",
        "detail": eff.llm.model if llm_configured else "rule-based extraction",
    })

    # Embedding — mirror LLM: target = endpoint, detail = model id
    emb = eff.embedding
    if emb.provider == "local":
        emb_target = "local-hash"
        emb_detail = "local-hash"
    elif emb.provider == "openai_compatible" and emb.base_url:
        emb_target = mask_url(emb.base_url)
        emb_detail = emb.model or emb.provider
    else:
        emb_target = emb.provider
        emb_detail = emb.model or emb.provider
    links.append({
        "id": "embedding",
        "name": "Embedding",
        "role": "ai",
        "status": "connected" if emb.provider else "error",
        "latency_ms": None,
        "target": emb_target,
        "detail": emb_detail,
        "engine": emb.provider,
    })

    db_ok = any(x["id"] == "database" and x["status"] == "connected" for x in links)
    neo_ok = any(x["id"] == "neo4j" and x["status"] in {"connected", "optional"} for x in links)
    ready = db_ok and neo_ok

    # legacy flat fields kept for dashboard compatibility
    database = next((x.get("engine") or x["detail"] for x in links if x["id"] == "database"), "error")
    if links[1]["status"] != "connected":
        database = f"error:{links[1]['detail']}"
    neo = next(x["status"] for x in links if x["id"] == "neo4j")
    redis = next(x["status"] for x in links if x["id"] == "redis")
    llm = next(x["status"] for x in links if x["id"] == "llm")

    return {
        "ready": ready,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "mode": "trust-aware-production-core",
        "database": database,
        "redis": redis,
        "llm": llm,
        "neo4j": neo,
        "embedding_provider": emb.provider,
        "embedding_model": emb.model,
        "queue": "arq" if redis == "connected" else "unavailable",
        "links": links,
    }
