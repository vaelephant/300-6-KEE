import copy,json
from pathlib import Path
import pytest
from sqlalchemy import create_engine,insert,select
from sqlalchemy.exc import IntegrityError
from app import models as m
from app.repository import Repository
E=Path(__file__).resolve().parents[2]/'contracts/examples'
def sample(n):return json.loads((E/(n+'.json')).read_text())
@pytest.fixture
def db():
 e=create_engine('sqlite://')
 with e.begin() as c:
  c.exec_driver_sql('PRAGMA foreign_keys=ON');m.metadata.create_all(c)
  c.execute(insert(m.patients),[{'tenant_id':'hospital_demo','patient_id':p} for p in ['patient_demo','other']])
  c.execute(insert(m.encounters).values(tenant_id='hospital_demo',patient_id='patient_demo',encounter_id='enc_demo'))
  yield c

def seed(c):
 r=Repository(c,'hospital_demo');r.add_asset(sample('asset-version'));r.add_anchor(sample('evidence-anchor'));return r

def test_roundtrip(db):
 r=seed(db);f=sample('clinical-fact');r.add_fact(f)
 assert r.get(m.fact_versions,'fact_version_id','fv_1')['payload']==f
 assert db.execute(select(m.fact_evidence)).first()
def test_revision(db):
 r=seed(db);f=sample('clinical-fact');r.add_fact(f)
 n=copy.deepcopy(f);n.update(version=2,fact_version_id='fv_2',supersedes_fact_version_id='fv_1');n['value']['value']='90';r.add_fact(n)
 assert r.get(m.fact_versions,'fact_version_id','fv_1')['payload']['value']['value']=='86'
def test_wrong_tenant(db):
 with pytest.raises(ValueError):Repository(db,'other').add_asset(sample('asset-version'))
def test_cross_patient(db):
 r=seed(db);f=sample('clinical-fact');f['scope']={'patient_id':'other','encounter_id':None}
 with pytest.raises(ValueError):r.add_fact(f)
def test_bad_predecessor(db):
 r=seed(db);f=sample('clinical-fact');f.update(version=2,supersedes_fact_version_id='missing')
 with pytest.raises(ValueError):r.add_fact(f)
def test_duplicate(db):
 r=seed(db)
 with pytest.raises(IntegrityError):r.add_asset(sample('asset-version'))
def test_database_scope_fk(db):
 seed(db)
 with pytest.raises(IntegrityError):db.execute(insert(m.anchors).values(tenant_id='hospital_demo',patient_id='other',anchor_id='bad',asset_version_id='av_1',payload={}))
def test_invalid_range(db):
 r=seed(db);a=sample('evidence-anchor');a['anchor_id']='bad';a['locator']={'kind':'media_segment','start_ms':10,'end_ms':1}
 with pytest.raises(ValueError):r.add_anchor(a)
