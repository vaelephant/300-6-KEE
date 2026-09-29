from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utcnow():
    return datetime.now(timezone.utc)

@dataclass
class Evidence:
    source: str
    excerpt: str
    source_type: str = "text"
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utcnow)

@dataclass
class KnowledgeObject:
    content: str
    source: str
    type: str = "claim"
    id: str = field(default_factory=lambda: str(uuid4()))
    canonical_key: str | None = None
    entities: list[str] = field(default_factory=list)
    relations: list[dict[str, str]] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    confidence: float = 0.5
    version: int = 1
    status: str = "active"
    supersedes_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def to_dict(self):
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        for ev in data["evidence"]:
            if hasattr(ev.get("created_at"), "isoformat"):
                ev["created_at"] = ev["created_at"].isoformat()
        return data
