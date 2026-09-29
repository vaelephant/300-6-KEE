"""知识信任分（kee-trust-v1）。

对单条 KnowledgeObject 打 0~1 分，供 Agent Runtime 过滤低质量上下文。
首页 Trust Intelligence 的平均分，来自多条 evaluate 结果再取 mean。
"""
from datetime import datetime, timezone
from math import exp
from app.models.knowledge import KnowledgeObject

# 六维权重，合计 1.0。改权重即换策略版本时记得同步 policy 名。
WEIGHTS = {
    "source_authority": 0.20,   # 来源是否像权威文档
    "evidence_strength": 0.20,  # 证据数量 / 多样 / 摘录长度
    "freshness": 0.15,          # 多久没更新
    "consistency": 0.20,        # 冲突与状态（审阅中会扣分）
    "usage_feedback": 0.10,     # 置信度与纠错反馈
    "human_verification": 0.15, # 是否人工确认过
}


class TrustService:
    def _source_authority(self, obj: KnowledgeObject) -> float:
        """来源权威性：优先读 metadata 覆盖值，否则用 source 字符串启发式。"""
        meta = obj.metadata or {}
        if isinstance(meta.get("source_authority"), (int, float)):
            return max(0.0, min(1.0, float(meta["source_authority"])))
        source = (obj.source or "").lower()
        # 文件名 / 来源标签里出现这些词 → 偏高
        if any(x in source for x in ("guideline", "standard", "official", "consensus", "journal")):
            return 0.90
        if any(x in source for x in ("expert", "reviewed", "curated")):
            return 0.82
        # 控制台手填、用户反馈 → 偏低
        if any(x in source for x in ("user", "console", "feedback")):
            return 0.58
        return 0.68  # 普通上传文档的默认档

    def _evidence_strength(self, obj: KnowledgeObject) -> float:
        """证据强度：无证据很低；多来源 + 更长摘录会抬分。"""
        evidence = obj.evidence or []
        if not evidence:
            return 0.35
        unique_sources = len({(e.source or "").strip().lower() for e in evidence if e.source})
        # 摘录越长（上限 300 字）贡献越大
        avg_excerpt = sum(min(len(e.excerpt or "") / 300, 1.0) for e in evidence) / len(evidence)
        return min(1.0, 0.45 + min(unique_sources, 4) * 0.10 + avg_excerpt * 0.15)

    def _freshness(self, obj: KnowledgeObject) -> float:
        """新鲜度：按更新后天数指数衰减，半衰期约 730 天，地板 0.35。"""
        dt = obj.updated_at or obj.created_at
        if not dt:
            return 0.6
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        days = max(0, (datetime.now(timezone.utc) - dt).days)
        return max(0.35, exp(-days / 730))

    def _consistency(self, obj: KnowledgeObject) -> float:
        """一致性：拒绝/归档最低；待审中偏低；冲突条目越多越低。"""
        if obj.status in {"rejected", "archived"}:
            return 0.20
        if obj.status == "review_required":
            return 0.48
        conflicts = len((obj.metadata or {}).get("conflicts_with", []))
        return max(0.45, 0.96 - conflicts * 0.10)

    def _usage_feedback(self, obj: KnowledgeObject) -> float:
        """使用反馈：以 confidence 为底，每次纠错扣 0.08。"""
        corrections = len((obj.metadata or {}).get("corrections", []))
        return max(0.25, min(1.0, obj.confidence - corrections * 0.08 + 0.08))

    def _human_verification(self, obj: KnowledgeObject) -> float:
        """人工验证：显式标记最高；已晋升版本次之；待审很低。"""
        meta = obj.metadata or {}
        if meta.get("human_verified") is True:
            return 1.0
        if obj.status == "active" and obj.version > 1:
            return 0.90  # 审阅通过后常会升 version
        if obj.status == "active":
            return 0.72
        if obj.status == "review_required":
            return 0.35
        return 0.20

    def evaluate(self, obj: KnowledgeObject) -> dict:
        """对单条知识加权汇总，并映射到 high / medium / guarded / low。"""
        factors = {
            "source_authority": self._source_authority(obj),
            "evidence_strength": self._evidence_strength(obj),
            "freshness": self._freshness(obj),
            "consistency": self._consistency(obj),
            "usage_feedback": self._usage_feedback(obj),
            "human_verification": self._human_verification(obj),
        }
        score = round(sum(factors[k] * WEIGHTS[k] for k in WEIGHTS), 4)
        if score >= 0.85:
            level = "high"
        elif score >= 0.65:
            level = "medium"
        elif score >= 0.45:
            level = "guarded"
        else:
            level = "low"
        return {
            "knowledge_id": obj.id,
            "trust_score": score,       # 0~1；UI 常 ×100 显示
            "trust_level": level,
            "factors": {k: round(v, 4) for k, v in factors.items()},
            "weights": WEIGHTS,
            "policy": "kee-trust-v1",
        }


trust_service = TrustService()
