import hashlib, re
from app.models.knowledge import Evidence, KnowledgeObject
from app.schemas.knowledge import KnowledgeCreate
from app.services.ai_provider import ai_provider

ENTITY_RE=re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}|[\u4e00-\u9fff]{2,12}")
SENTENCE_RE=re.compile(r"(?<=[。！？!?；;])\s*|\n+")
REL_PATTERNS=[re.compile(r"(.{2,20}?)(?:是|属于|用于|导致|推荐|支持)(.{2,30})")]
class UnderstandingService:
 def normalize(self,text): return re.sub(r"\s+"," ",text).strip()
 def claims(self,text):
  p=[self.normalize(x) for x in SENTENCE_RE.split(text) if self.normalize(x)]; return p or [self.normalize(text)]
 def entities(self,text):
  seen=set(); out=[]
  for t in ENTITY_RE.findall(text):
   k=t.lower()
   if k not in seen: seen.add(k); out.append(t)
  return out[:24]
 def relations(self,text,entities):
  out=[]
  for p in REL_PATTERNS:
   for m in p.finditer(text): out.append({'source':m.group(1).strip(),'predicate':'related_to','target':m.group(2).strip()})
  if not out and len(entities)>=2: out=[{'source':entities[0],'predicate':'co_occurs','target':x} for x in entities[1:4]]
  return out[:12]
 def canonical_key(self,content,domain):
  normalized=re.sub(r"[^\w\u4e00-\u9fff]+","",content.lower()); return hashlib.sha256(f"{domain or 'general'}:{normalized[:256]}".encode()).hexdigest()[:24]
 async def build_objects_async(self,data:KnowledgeCreate):
  try:
   ai=await ai_provider.extract(data.content)
  except Exception:
   ai=None
  claims=(ai or {}).get('claims') or self.claims(data.content)
  global_entities=(ai or {}).get('entities') or []
  global_rel=(ai or {}).get('relations') or []
  result=[]
  for claim in claims:
   md=dict(data.metadata); md['extraction']='llm' if ai else 'local';
   if data.domain: md['domain']=data.domain
   ents=list(dict.fromkeys(global_entities+self.entities(claim)))[:24]
   rels=global_rel or self.relations(claim,ents)
   result.append(KnowledgeObject(content=claim,source=data.source,type=data.type,canonical_key=self.canonical_key(claim,data.domain),entities=ents,relations=rels,evidence=[Evidence(source=data.source,excerpt=claim)],confidence=float(md.pop('confidence',.78 if ai else .65)),metadata=md))
  return result
 def build_objects(self,data):
  # synchronous compatibility for tests / legacy paths
  result=[]
  for claim in self.claims(data.content):
   md=dict(data.metadata); md['extraction']='local';
   if data.domain: md['domain']=data.domain
   ents=self.entities(claim)
   result.append(KnowledgeObject(content=claim,source=data.source,type=data.type,canonical_key=self.canonical_key(claim,data.domain),entities=ents,relations=self.relations(claim,ents),evidence=[Evidence(source=data.source,excerpt=claim)],confidence=float(md.pop('confidence',.65)),metadata=md))
  return result
understanding_service=UnderstandingService()
