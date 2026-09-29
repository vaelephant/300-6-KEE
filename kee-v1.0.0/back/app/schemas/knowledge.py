from pydantic import BaseModel, Field
from typing import Any

class KnowledgeCreate(BaseModel):
    content: str = Field(min_length=1)
    source: str = Field(min_length=1)
    type: str = "claim"
    domain: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    domain: str | None = None
    top_k: int = Field(default=8, ge=1, le=50)
    include_superseded: bool = False

class FeedbackRequest(BaseModel):
    knowledge_id: str | None = None
    query: str = ""
    rating: int = Field(ge=-1, le=1)
    correction: str | None = None
    source: str = "user_feedback"

class EvolveRequest(BaseModel):
    content: str = Field(min_length=1)
    source: str = Field(min_length=1)
    type: str = "claim"
    domain: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    auto_promote: bool = False
