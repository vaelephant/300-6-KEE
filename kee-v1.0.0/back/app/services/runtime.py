from datetime import datetime, timezone
from uuid import uuid4

from app.services.audit import audit_service
from app.services.retrieval import retrieval_service
from app.services.trust import trust_service

AGENT_PROTOCOL = "kee-agent-context/1.0"
AGENT_INSTRUCTIONS = (
    "Use only grounded context when answering. "
    "Preserve KEE citation ids in the final answer. "
    "If grounded=false, say evidence is insufficient."
)


def _knowledge_dict(obj) -> dict:
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if isinstance(obj, dict):
        return obj
    return {"id": getattr(obj, "id", None), "content": getattr(obj, "content", str(obj))}


class RuntimeService:
    async def context(
        self,
        question: str,
        top_k: int = 6,
        domain: str | None = None,
        min_trust: float = 0.45,
        include_guarded: bool = True,
        *,
        serialize: bool = False,
        source: str = "api",
    ):
        raw = await retrieval_service.query(question, max(top_k * 3, 12), domain, False)
        selected = []
        for hit in raw:
            obj = hit["knowledge"]
            trust = trust_service.evaluate(obj)
            if trust["trust_score"] < min_trust:
                continue
            if not include_guarded and trust["trust_level"] in {"guarded", "low"}:
                continue
            selected.append((hit, trust))
        selected = selected[:top_k]
        evidence = []
        citations = []
        knowledge = []
        for idx, (hit, trust) in enumerate(selected, 1):
            obj = hit["knowledge"]
            kid = obj.id
            cite = f"[K{idx}]"
            citations.append(
                {
                    "id": cite,
                    "knowledge_id": kid,
                    "source": obj.source,
                    "version": obj.version,
                    "trust_score": trust["trust_score"],
                }
            )
            knowledge.append(
                {
                    "citation": cite,
                    "score": hit["score"],
                    "trust": trust,
                    "knowledge": _knowledge_dict(obj) if serialize else obj,
                }
            )
            for ev in obj.evidence[:3]:
                evidence.append(
                    {
                        "citation": cite,
                        "knowledge_id": kid,
                        "source": ev.source,
                        "excerpt": ev.excerpt,
                        "source_type": ev.source_type,
                    }
                )
        context_text = "\n\n".join(
            f"{x['citation']} {x['knowledge']['content'] if serialize else x['knowledge'].content}"
            for x in knowledge
        )
        pack = {
            "request_id": str(uuid4()),
            "question": question,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "policy": {"name": "kee-runtime-v1", "min_trust": min_trust, "top_k": top_k},
            "context": context_text,
            "knowledge": knowledge,
            "evidence": evidence,
            "citations": citations,
            "grounded": bool(knowledge),
        }
        try:
            await audit_service.record(
                "runtime_context",
                detail={
                    "request_id": pack["request_id"],
                    "source": source,
                    "grounded": pack["grounded"],
                    "citation_count": len(citations),
                    "question_len": len(question),
                },
            )
        except Exception:
            pass
        return pack

    async def agent_pack(
        self,
        question: str,
        top_k: int = 6,
        domain: str | None = None,
        min_trust: float = 0.45,
        include_guarded: bool = True,
        *,
        source: str = "api",
    ) -> dict:
        pack = await self.context(
            question=question,
            top_k=top_k,
            domain=domain,
            min_trust=min_trust,
            include_guarded=include_guarded,
            serialize=True,
            source=source,
        )
        return {
            "protocol": AGENT_PROTOCOL,
            "instructions": AGENT_INSTRUCTIONS,
            "context_pack": pack,
        }


runtime_service = RuntimeService()
