from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, Integer, DateTime, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

def utcnow(): return datetime.now(timezone.utc)
class Base(DeclarativeBase): pass
class KnowledgeRow(Base):
    __tablename__="knowledge_objects"
    id: Mapped[str]=mapped_column(String(64),primary_key=True)
    content: Mapped[str]=mapped_column(Text)
    source: Mapped[str]=mapped_column(String(512),default="unknown")
    type: Mapped[str]=mapped_column(String(64),default="claim")
    canonical_key: Mapped[str|None]=mapped_column(String(512),nullable=True,index=True)
    entities: Mapped[list]=mapped_column(JSON,default=list)
    relations: Mapped[list]=mapped_column(JSON,default=list)
    evidence: Mapped[list]=mapped_column(JSON,default=list)
    confidence: Mapped[float]=mapped_column(Float,default=.5)
    version: Mapped[int]=mapped_column(Integer,default=1)
    status: Mapped[str]=mapped_column(String(64),default="active",index=True)
    supersedes_id: Mapped[str|None]=mapped_column(String(64),nullable=True)
    meta: Mapped[dict]=mapped_column("metadata",JSON,default=dict)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
class EventRow(Base):
    __tablename__="evolution_events"
    id: Mapped[str]=mapped_column(String(64),primary_key=True)
    event_type: Mapped[str]=mapped_column(String(96),index=True)
    knowledge_id: Mapped[str|None]=mapped_column(String(64),nullable=True,index=True)
    detail: Mapped[dict]=mapped_column(JSON,default=dict)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
class DocumentRow(Base):
    __tablename__="documents"
    id: Mapped[str]=mapped_column(String(64),primary_key=True)
    filename: Mapped[str]=mapped_column(String(512))
    path: Mapped[str]=mapped_column(String(1024))
    content_type: Mapped[str]=mapped_column(String(128),default="")
    status: Mapped[str]=mapped_column(String(64),default="queued")
    domain: Mapped[str]=mapped_column(String(128),default="general")
    chunks: Mapped[int]=mapped_column(Integer,default=0)
    claims: Mapped[int]=mapped_column(Integer,default=0)
    job_id: Mapped[str|None]=mapped_column(String(64),nullable=True,index=True)
    error: Mapped[str|None]=mapped_column(Text,nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
class JobRow(Base):
    __tablename__="jobs"
    id: Mapped[str]=mapped_column(String(64),primary_key=True)
    kind: Mapped[str]=mapped_column(String(64),index=True)
    document_id: Mapped[str|None]=mapped_column(String(64),nullable=True,index=True)
    status: Mapped[str]=mapped_column(String(64),default="queued",index=True)
    progress: Mapped[int]=mapped_column(Integer,default=0)
    total: Mapped[int]=mapped_column(Integer,default=0)
    detail: Mapped[dict]=mapped_column(JSON,default=dict)
    error: Mapped[str|None]=mapped_column(Text,nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
class KnowledgeVersionRow(Base):
    __tablename__="knowledge_versions"
    id: Mapped[str]=mapped_column(String(64),primary_key=True)
    knowledge_id: Mapped[str]=mapped_column(String(64),index=True)
    version: Mapped[int]=mapped_column(Integer,index=True)
    content: Mapped[str]=mapped_column(Text)
    status: Mapped[str]=mapped_column(String(64))
    confidence: Mapped[float]=mapped_column(Float)
    snapshot: Mapped[dict]=mapped_column(JSON,default=dict)
    reason: Mapped[str]=mapped_column(String(128),default="update")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)
