"""Initialize synthetic identities and a demo-only registered query."""
import json,os,hashlib
from pathlib import Path
from sqlalchemy import create_engine,insert,select
from . import models as m
from .repository import validate
from .service import now
E=Path(__file__).resolve().parents[2]/'contracts/examples'
def payload():
 d={k:json.loads((E/(n+'.json')).read_text()) for k,n in [('asset','asset-version'),('anchor','evidence-anchor'),('fact','clinical-fact')]};d['source_record']={'result_value':'86'};return d
def initialize(c):
 t='hospital_demo'
 if not c.execute(select(m.patients).where(m.patients.c.tenant_id==t,m.patients.c.patient_id=='patient_demo')).first():
  c.execute(insert(m.patients).values(tenant_id=t,patient_id='patient_demo'))
  c.execute(insert(m.encounters).values(tenant_id=t,patient_id='patient_demo',encounter_id='enc_demo'))
 if not c.execute(select(m.queries).where(m.queries.c.tenant_id==t,m.queries.c.query_id=='creatinine_latest_two')).first():
  q=json.loads((E/'query-definition.json').read_text());q['lifecycle']='published';q['approval']={'reviewer_id':'demo_bootstrap_only','approved_at':now(),'test_run_id':'demo_not_clinical_approval'}
  q['executor']={'kind':'registered_api','artifact_id':'app.service.query','artifact_sha256':hashlib.sha256(Path(__file__).with_name('service.py').read_bytes()).hexdigest()};validate('query-definition',q)
  c.execute(insert(m.queries).values(tenant_id=t,query_id=q['query_id'],version=1,lifecycle='published',payload=q))
if __name__=='__main__':
 engine=create_engine(os.getenv('DATABASE_URL','sqlite:///development.db'))
 with engine.begin() as c:initialize(c)
 Path('demo-ingest.json').write_text(json.dumps(payload(),ensure_ascii=False,indent=2))
 print('Synthetic identities and demo query ready; wrote demo-ingest.json')
