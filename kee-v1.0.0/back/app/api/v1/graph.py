from fastapi import APIRouter
from app.repositories.database import repository

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("")
async def graph(limit: int = 200):
    items = await repository.list(limit)
    nodes = {}
    edges = []
    for k in items:
        kid = "k:" + k.id
        nodes[kid] = {
            "id": kid,
            "knowledge_id": k.id,
            "label": k.content[:72],
            "content": k.content,
            "kind": "knowledge",
            "status": k.status,
            "confidence": k.confidence,
            "version": k.version,
            "source": k.source,
            "entities": k.entities[:12],
        }
        for ent in k.entities[:12]:
            eid = "e:" + ent.lower()
            nodes[eid] = {"id": eid, "label": ent, "kind": "entity", "name": ent}
            edges.append({"source": kid, "target": eid, "predicate": "mentions"})
        for r in k.relations[:12]:
            a = "e:" + str(r.get("source", "")).lower()
            b = "e:" + str(r.get("target", "")).lower()
            if a != "e:" and b != "e:":
                nodes.setdefault(
                    a, {"id": a, "label": r.get("source"), "kind": "entity", "name": r.get("source")}
                )
                nodes.setdefault(
                    b, {"id": b, "label": r.get("target"), "kind": "entity", "name": r.get("target")}
                )
                edges.append(
                    {"source": a, "target": b, "predicate": r.get("predicate", "related_to")}
                )
    return {"nodes": list(nodes.values()), "edges": edges}
