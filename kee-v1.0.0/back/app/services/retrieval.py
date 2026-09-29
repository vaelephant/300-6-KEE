import re
from app.repositories.database import repository
from app.integrations.vector import vector_provider
from app.services.embedding import cosine


class RetrievalService:
    def _tokens(self, text):
        return set(re.findall(r"[A-Za-z0-9_-]+|[\u4e00-\u9fff]", text.lower()))

    async def query(self, question, top_k=8, domain=None, include_superseded=False):
        qtok = self._tokens(question)
        qv = vector_provider.embed([question])[0]
        scored = []
        for item in await repository.list():
            if not include_superseded and item.status in {"superseded", "archived", "rejected"}:
                continue
            if domain and item.metadata.get("domain") != domain:
                continue
            corpus = item.content + " " + " ".join(item.entities)
            tok = self._tokens(corpus)
            lexical = len(qtok & tok) / max(1, len(qtok))
            cv = vector_provider.embed([corpus])[0]
            semantic = max(0.0, cosine(qv, cv))
            entity = min(1.0, len(qtok & {x.lower() for x in item.entities}) / max(1, len(qtok)))
            score = lexical * 0.38 + semantic * 0.37 + entity * 0.10 + item.confidence * 0.15
            scored.append((score, item, lexical, semantic))
        scored.sort(key=lambda x: (x[0], x[1].updated_at), reverse=True)
        return [
            {
                "score": round(s, 4),
                "signals": {
                    "lexical": round(l, 4),
                    "semantic": round(v, 4),
                    "confidence": i.confidence,
                },
                "knowledge": i,
            }
            for s, i, l, v in scored[:top_k]
        ]


retrieval_service = RetrievalService()
