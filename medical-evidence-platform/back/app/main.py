import os,json,secrets
from contextlib import contextmanager
from fastapi import FastAPI,Depends,HTTPException
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from pydantic import BaseModel,ConfigDict
from sqlalchemy import create_engine,event,select
from sqlalchemy.exc import IntegrityError
from jsonschema import ValidationError
from . import models as m
from .repository import Repository
from .service import ingest,query
class IngestBody(BaseModel):
 model_config=ConfigDict(extra='forbid')
 asset:dict
 anchor:dict
 fact:dict
 source_record:dict
class QueryBody(BaseModel):
 model_config=ConfigDict(extra='forbid')
 patient_id:str
 encounter_id:str|None=None

def create_app(engine=None,principals=None):
 app=FastAPI(title='Medical Evidence Platform',version='0.9.0')
 engine=engine if engine is not None else create_engine(os.getenv('DATABASE_URL','sqlite:///development.db'))
 if engine.dialect.name=='sqlite':
  @event.listens_for(engine,'connect')
  def foreign_keys(conn,record):conn.execute('PRAGMA foreign_keys=ON')
 credentials=principals if principals is not None else json.loads(os.getenv('EVIDENCE_PRINCIPALS_JSON','{}'))
 bearer=HTTPBearer()
 def auth(token:HTTPAuthorizationCredentials=Depends(bearer)):
  for key,p in credentials.items():
   if secrets.compare_digest(key,token.credentials):return p
  raise HTTPException(401,'Invalid credential')
 def allow(p,patient,permission):
  if permission not in p['permissions'] or patient not in p['patients']:raise HTTPException(403,'Not authorized')
 @app.get('/v1/patients')
 def patients(p=Depends(auth)):
  if 'read' not in p['permissions']:raise HTTPException(403,'Not authorized')
  with engine.begin() as c:
   rows=c.execute(select(m.patients).where(m.patients.c.tenant_id==p['tenant_id'],m.patients.c.patient_id.in_(p['patients']))).mappings().all()
   return {'items':[{'patient_id':row['patient_id'],'display_name':row['patient_id'],'encounters':[{'encounter_id':e['encounter_id']} for e in c.execute(select(m.encounters).where(m.encounters.c.tenant_id==p['tenant_id'],m.encounters.c.patient_id==row['patient_id'])).mappings()]} for row in rows]}
 @app.get('/health')
 def health():return {'status':'ok'}
 @app.post('/v1/ingestion/lab-records')
 def add(body:IngestBody,p=Depends(auth)):
  data=body.model_dump();patient=data['fact'].get('scope',{}).get('patient_id');allow(p,patient,'ingest')
  try:
   with engine.begin() as c:return ingest(c,p['tenant_id'],data)
  except (ValueError,ValidationError,IntegrityError):raise HTTPException(422,'Invalid record or conflicting version')
 @app.post('/v1/queries/creatinine-latest-two')
 def lookup(body:QueryBody,p=Depends(auth)):
  allow(p,body.patient_id,'read')
  try:
   with engine.begin() as c:return query(c,p['tenant_id'],body.patient_id,body.encounter_id,p['actor_id'])
  except ValueError:raise HTTPException(409,'Query unavailable')
 @app.get('/v1/evidence/{anchor_id}')
 def evidence(anchor_id:str,p=Depends(auth)):
  with engine.begin() as c:
   r=Repository(c,p['tenant_id']);a=r.get(m.anchors,'anchor_id',anchor_id)
   if not a:raise HTTPException(404,'Evidence not found')
   allow(p,a['patient_id'],'read')
   av=r.get(m.asset_versions,'asset_version_id',a['asset_version_id']);src=r.get(m.source_records,'asset_version_id',a['asset_version_id'])
   return {'anchor':a['payload'],'asset':av['payload'],'source_record':src['payload'] if src else None}
 from .document_api import attach
 document_search=attach(app,engine,auth,allow)
 from .reviews import attach as attach_reviews
 attach_reviews(app,engine,auth,allow)
 from .answering import attach as attach_answering
 attach_answering(app,engine,auth,allow,document_search)
 return app
app=create_app()
