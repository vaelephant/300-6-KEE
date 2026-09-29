from difflib import SequenceMatcher
from app.models.knowledge import KnowledgeObject, Evidence, utcnow
from app.repositories.database import repository
from app.services.understanding import understanding_service
from app.services.audit import audit_service

class EvolutionService:
    def similarity(self, a: str, b: str) -> float:
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    async def feedback(self, knowledge_id: str | None, rating: int, correction: str | None = None, source: str = "user_feedback"):
        if not knowledge_id:
            return {"accepted": True, "action": "queued_for_analysis"}
        item = await repository.get(knowledge_id)
        if not item:
            return {"accepted": False, "reason": "knowledge_not_found"}
        item.confidence = round(max(0.0, min(1.0, item.confidence + rating * 0.05)), 4)
        item.updated_at = utcnow()
        if correction:
            item.metadata.setdefault("corrections", []).append({"content": correction, "source": source})
            item.status = "review_required"
        await repository.save(item)
        return {"accepted": True, "knowledge_id": item.id, "version": item.version, "confidence": item.confidence, "status": item.status}

    async def evolve(self, candidate: KnowledgeObject, auto_promote: bool = False):
        active = [x for x in await repository.list() if x.status not in {"superseded", "archived"}]
        related = []
        candidate_entities = {x.lower() for x in candidate.entities}
        for old in active:
            entity_overlap = candidate_entities & {x.lower() for x in old.entities}
            sim = self.similarity(candidate.content, old.content)
            if entity_overlap or sim >= 0.55:
                related.append((sim, old))
        related.sort(key=lambda x: x[0], reverse=True)

        if not related:
            await repository.add(candidate)
            await audit_service.record("knowledge_created", candidate.id)
            return {"decision": "new", "candidate": candidate, "conflicts": []}

        best_sim, best = related[0]
        if best_sim >= 0.92:
            best.evidence.append(Evidence(source=candidate.source, excerpt=candidate.content))
            best.confidence = round(min(0.99, best.confidence + 0.03), 4)
            best.updated_at = utcnow()
            await repository.save(best)
            await audit_service.record("knowledge_reinforced", best.id, {"similarity": round(best_sim,4)})
            return {"decision": "reinforced", "knowledge": best, "similarity": round(best_sim, 4), "conflicts": []}

        candidate.status = "review_required"
        candidate.metadata["conflicts_with"] = [x.id for _, x in related[:5]]
        candidate.metadata["conflict_reason"] = "related entities with materially different claim"
        await repository.add(candidate)
        await audit_service.record("conflict_detected", candidate.id, {"conflicts": candidate.metadata.get("conflicts_with", [])})
        conflicts = [{"knowledge_id": x.id, "content": x.content, "similarity": round(s, 4)} for s, x in related[:5]]

        if auto_promote and candidate.confidence > best.confidence + 0.15:
            best.status = "superseded"
            best.updated_at = utcnow()
            candidate.status = "active"
            candidate.version = best.version + 1
            candidate.supersedes_id = best.id
            await repository.save(best); await repository.save(candidate)
            return {"decision": "promoted", "knowledge": candidate, "superseded": best.id, "conflicts": conflicts}
        return {"decision": "review_required", "candidate": candidate, "conflicts": conflicts}

    async def review(self, candidate_id: str, action: str):
        candidate = await repository.get(candidate_id)
        if not candidate: return {"accepted": False, "reason": "knowledge_not_found"}
        if action == "reject":
            candidate.status = "rejected"; candidate.updated_at = utcnow(); await repository.save(candidate); await audit_service.record("review_rejected", candidate.id)
            return {"accepted": True, "action": "rejected", "knowledge": candidate}
        if action != "approve": return {"accepted": False, "reason": "invalid_action"}
        conflicts = candidate.metadata.get("conflicts_with", [])
        prior = None
        for cid in conflicts:
            old = await repository.get(cid)
            if old and old.status == "active":
                prior = old; break
        if prior:
            prior.status = "superseded"; prior.updated_at = utcnow(); await repository.save(prior)
            candidate.version = prior.version + 1; candidate.supersedes_id = prior.id
        candidate.status = "active"; candidate.updated_at = utcnow(); await repository.save(candidate); await audit_service.record("review_approved", candidate.id, {"supersedes": candidate.supersedes_id})
        return {"accepted": True, "action": "approved", "knowledge": candidate}

evolution_service = EvolutionService()
