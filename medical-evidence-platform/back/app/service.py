import hashlib,json,uuid
from datetime import datetime,timezone
from sqlalchemy import select,insert
from . import models as m
from .repository import Repository,validate

def now():return datetime.now(timezone.utc).isoformat()
def ingest(c,tenant,p):
    r=Repository(c,tenant)
    a,anchor,f=p['asset'],p['anchor'],p['fact']
    for kind,x in [('asset-version',a),('evidence-anchor',anchor),('clinical-fact',f)]:r.check(kind,x)
    if a['scope']!=f['scope'] or anchor['asset_version_id']!=a['asset_version_id'] or f['anchor_ids']!=[anchor['anchor_id']]:raise ValueError('inconsistent ingestion references')
    if a['modality']!='structured' or anchor['locator']['kind']!='field':raise ValueError('only structured field ingestion supported')
    loc=anchor['locator']
    if loc['record_key']!=a['source']['record_key']:raise ValueError('source key mismatch')
    if f['fact_type']!='observation' or f['concept']['system']!='local_demo' or f['concept']['code']!='CREA':raise ValueError('only configured demo CREA mapping supported')
    if f['value']['kind']!='quantity' or str(p['source_record'].get(loc['field_path']))!=f['value']['raw_value']:raise ValueError('source value mismatch')
    if f['value']['comparator']!='eq' or f['value']['value']!=f['value']['raw_value']:raise ValueError('only exact, unconverted values supported')
    body=json.dumps(p['source_record'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    a=json.loads(json.dumps(a));a['content']={'object_key':'db:'+a['asset_version_id'],'sha256':hashlib.sha256(body).hexdigest(),'media_type':'application/json','size_bytes':len(body)}
    prior=r.get(m.asset_versions,'asset_version_id',a['asset_version_id'])
    if prior:
        oldf=r.get(m.fact_versions,'fact_version_id',f['fact_version_id']);olda=r.get(m.anchors,'anchor_id',anchor['anchor_id'])
        if prior['payload']==a and oldf and oldf['payload']==f and olda and olda['payload']==anchor:return {'status':'unchanged','fact_version_id':f['fact_version_id']}
        raise ValueError('existing version differs; create a new version')
    r.add_asset(a);r.add_anchor(anchor);r.add_fact(f)
    c.execute(insert(m.source_records).values(tenant_id=tenant,asset_version_id=a['asset_version_id'],payload=p['source_record']))
    return {'status':'created','fact_version_id':f['fact_version_id']}

def query(c,tenant,patient,encounter,actor):
    r=Repository(c,tenant);rows=c.execute(select(m.fact_versions.c.payload).where(m.fact_versions.c.tenant_id==tenant,m.fact_versions.c.patient_id==patient)).scalars()
    latest={}
    for f in rows:
        if f['fact_id'] not in latest or latest[f['fact_id']]['version']<f['version']:latest[f['fact_id']]=f
    facts=[];issues=[]
    for f in latest.values():
        if encounter is not None and f['scope']['encounter_id']!=encounter:continue
        if f['concept']['system']!='local_demo' or f['concept']['code']!='CREA' or f['fact_type']!='observation':continue
        if f['publication_status']!='published' or f['record_status'] not in ('final','corrected'):continue
        if f['value']['kind']!='quantity' or f['value']['specimen']!='serum':continue
        if f['event_time']['precision']!='datetime':issues.append({'code':'MISSING_PRECISE_TIME','message':'存在无法精确排序的记录'});continue
        facts.append(f)
    facts.sort(key=lambda f:(datetime.fromisoformat(f['event_time']['value']),f['fact_id']),reverse=True);facts=facts[:2]
    evidence=[]
    for f in facts:
        for aid in f['anchor_ids']:
            a=r.get(m.anchors,'anchor_id',aid)
            evidence.append({'evidence_id':aid,'anchor_id':aid,'asset_version_id':a['asset_version_id']})
    if len(facts)<2:issues.append({'code':'INSUFFICIENT_OBSERVATIONS','message':'不足两次有效结果'})
    qid='creatinine_latest_two';qd=c.execute(select(m.queries).where(m.queries.c.tenant_id==tenant,m.queries.c.query_id==qid,m.queries.c.version==1)).mappings().one_or_none()
    if not qd or qd['lifecycle']!='published':raise ValueError('query not published; run demo initialization')
    ident=uuid.uuid4().hex
    bundle={'schema_version':'1.0.0','tenant_id':tenant,'bundle_id':'b_'+ident,'query_run_id':'q_'+ident,'query_definition':{'id':qid,'version':1},'scope':{'patient_id':patient,'encounter_id':encounter},'snapshot_id':'s_'+ident,'created_at':now(),'execution_status':'completed','evidence_status':'insufficient' if issues else 'supported','coverage':[{'system_id':'lis_demo','status':'unknown','synced_through':None,'limitations':['仅包含手动导入记录，尚未连接LIS同步水位']}],'facts':facts,'evidence':list({e['evidence_id']:e for e in evidence}.values()),'conflicts':[],'calculations':[],'issues':issues,'next_cursor':None}
    validate('evidence-bundle',bundle)
    c.execute(insert(m.runs).values(tenant_id=tenant,query_run_id=bundle['query_run_id'],patient_id=patient,query_id=qid,query_version=1,actor_id=actor,purpose='demo_lookup',snapshot_id=bundle['snapshot_id'],status='completed'))
    c.execute(insert(m.bundles).values(tenant_id=tenant,bundle_id=bundle['bundle_id'],patient_id=patient,query_run_id=bundle['query_run_id'],payload=bundle))
    return bundle
