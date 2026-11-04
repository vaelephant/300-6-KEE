"""Write only through a transaction and validated contracts; no authentication API yet."""
import json
from pathlib import Path
from sqlalchemy import select,insert
from jsonschema import Draft202012Validator,FormatChecker
from referencing import Registry,Resource
from . import models as m
ROOT=Path(__file__).resolve().parents[2]/'contracts'
SCHEMAS={p.name:json.loads(p.read_text()) for p in (ROOT/'schemas').glob('*.json')}
REG=Registry().with_resources((k,Resource.from_contents(v)) for k,v in SCHEMAS.items())
def validate(kind,p):Draft202012Validator(SCHEMAS[kind+'.schema.json'],registry=REG,format_checker=FormatChecker()).validate(p)
class Repository:
    def __init__(self,conn,tenant_id):self.c=conn;self.tenant=tenant_id
    def check(self,kind,p):
        validate(kind,p)
        if p['tenant_id']!=self.tenant:raise ValueError('tenant mismatch')
    def get(self,t,idfield,value):
        return self.c.execute(select(t).where(t.c.tenant_id==self.tenant,t.c[idfield]==value)).mappings().one_or_none()
    def identity(self,t,key,value,scope):
        old=self.get(t,key,value)
        if old:
            if old['patient_id']!=scope['patient_id'] or old['encounter_id']!=scope['encounter_id']:raise ValueError('identity scope changed')
        else:self.c.execute(insert(t).values(tenant_id=self.tenant,**{key:value},**scope))
    def predecessor(self,t,idfield,entity,p,field):
        prev=p[field]
        if p['version']==1:
            if prev is not None:raise ValueError('first version cannot supersede')
        else:
            row=self.get(t,idfield,prev)
            if not row or row[entity]!=p[entity] or row['version']!=p['version']-1:raise ValueError('invalid predecessor')
    def add_asset(self,p):
        self.check('asset-version',p)
        self.predecessor(m.asset_versions,'asset_version_id','asset_id',p,'supersedes_asset_version_id')
        self.identity(m.assets,'asset_id',p['asset_id'],p['scope'])
        self.c.execute(insert(m.asset_versions).values(tenant_id=self.tenant,asset_version_id=p['asset_version_id'],asset_id=p['asset_id'],patient_id=p['scope']['patient_id'],version=p['version'],payload=p))
    def add_anchor(self,p):
        self.check('evidence-anchor',p)
        asset=self.get(m.asset_versions,'asset_version_id',p['asset_version_id'])
        if not asset:raise ValueError('missing asset')
        loc=p['locator'];kind=loc['kind']
        if kind=='text' and loc['end']<=loc['start']:raise ValueError('invalid text range')
        if kind=='media_segment' and loc['end_ms']<=loc['start_ms']:raise ValueError('invalid media range')
        if kind=='page_region' and (loc['x']+loc['width']>1 or loc['y']+loc['height']>1):raise ValueError('invalid page region')
        self.c.execute(insert(m.anchors).values(tenant_id=self.tenant,anchor_id=p['anchor_id'],asset_version_id=p['asset_version_id'],patient_id=asset['patient_id'],payload=p))
    def add_fact(self,p):
        self.check('clinical-fact',p)
        self.predecessor(m.fact_versions,'fact_version_id','fact_id',p,'supersedes_fact_version_id')
        for aid in p['anchor_ids']:
            a=self.get(m.anchors,'anchor_id',aid)
            if not a or a['patient_id']!=p['scope']['patient_id']:raise ValueError('invalid evidence scope')
            av=self.get(m.asset_versions,'asset_version_id',a['asset_version_id'])
            if av['payload']['scope']['encounter_id']!=p['scope']['encounter_id']:raise ValueError('encounter mismatch')
        for fid in p['derivation']['input_fact_version_ids']:
            f=self.get(m.fact_versions,'fact_version_id',fid)
            if not f or f['patient_id']!=p['scope']['patient_id']:raise ValueError('invalid derivation input')
        self.identity(m.facts,'fact_id',p['fact_id'],p['scope'])
        self.c.execute(insert(m.fact_versions).values(tenant_id=self.tenant,patient_id=p['scope']['patient_id'],fact_id=p['fact_id'],fact_version_id=p['fact_version_id'],version=p['version'],concept_code=p['concept']['code'],publication_status=p['publication_status'],payload=p))
        for aid in p['anchor_ids']:self.c.execute(insert(m.fact_evidence).values(tenant_id=self.tenant,patient_id=p['scope']['patient_id'],fact_version_id=p['fact_version_id'],anchor_id=aid))
