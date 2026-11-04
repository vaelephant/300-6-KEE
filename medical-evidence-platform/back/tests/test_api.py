import copy
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app import models as m
from app.main import create_app
from app.demo import initialize,payload

def client(permissions=None):
 e=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
 app=create_app(e,{'test-token':{'tenant_id':'hospital_demo','actor_id':'demo','patients':['patient_demo'],'permissions':permissions if permissions is not None else ['read','ingest']}})
 with e.begin() as c:m.metadata.create_all(c);initialize(c)
 return TestClient(app)
H={'Authorization':'Bearer test-token'}
def test_api_end_to_end():
 c=client();d=payload()
 assert c.post('/v1/ingestion/lab-records',json=d,headers=H).json()['status']=='created'
 assert c.post('/v1/ingestion/lab-records',json=d,headers=H).json()['status']=='unchanged'
 b=c.post('/v1/queries/creatinine-latest-two',json={'patient_id':'patient_demo'},headers=H).json()
 assert len(b['facts'])==1 and b['evidence_status']=='insufficient'
 assert c.get('/v1/evidence/anchor_1',headers=H).json()['source_record']['result_value']=='86'
def test_denied():
 c=client()
 assert c.post('/v1/queries/creatinine-latest-two',json={'patient_id':'other'},headers=H).status_code==403
 assert c.get('/v1/evidence/anchor_1').status_code in (401,403)
def test_revision_cancel_not_fallback():
 c=client();d=payload();assert c.post('/v1/ingestion/lab-records',json=d,headers=H).status_code==200
 d['asset'].update(asset_version_id='av_2',version=2,supersedes_asset_version_id='av_1',record_status='cancelled')
 d['anchor'].update(anchor_id='anchor_2',asset_version_id='av_2')
 d['fact'].update(fact_version_id='fv_2',version=2,supersedes_fact_version_id='fv_1',anchor_ids=['anchor_2'],record_status='cancelled')
 assert c.post('/v1/ingestion/lab-records',json=d,headers=H).status_code==200
 assert c.post('/v1/queries/creatinine-latest-two',json={'patient_id':'patient_demo'},headers=H).json()['facts']==[]
def test_source_mismatch():
 c=client();d=payload();d['source_record']['result_value']='999'
 assert c.post('/v1/ingestion/lab-records',json=d,headers=H).status_code==422

def test_authorized_patients():
 c=client();r=c.get('/v1/patients',headers=H)
 assert r.status_code==200 and [p['patient_id'] for p in r.json()['items']]==['patient_demo']
 assert r.json()['items'][0]['encounters']==[{'encounter_id':'enc_demo'}]
 assert c.get('/v1/patients').status_code in (401,403)

def test_demo_sequence():
 from app.make_samples import record
 c=client()
 a=record('a','86','2026-09-27T08:00:00+08:00');b=record('b','92','2026-09-29T09:00:00+08:00')
 for d in [a,b]:assert c.post('/v1/ingestion/lab-records',json=d,headers=H).status_code==200
 def results():return c.post('/v1/queries/creatinine-latest-two',json={'patient_id':'patient_demo'},headers=H).json()['facts']
 assert [f['value']['value'] for f in results()]==['92','86']
 for version,value,status in [(2,'90','corrected'),(3,'90','cancelled')]:
  d=record('b',value,'2026-09-29T09:00:00+08:00',version,status)
  assert c.post('/v1/ingestion/lab-records',json=d,headers=H).status_code==200
  assert [f['value']['value'] for f in results()]==(['90','86'] if version==2 else ['86'])
