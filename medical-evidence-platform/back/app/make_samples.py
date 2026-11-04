import json
from pathlib import Path
from .demo import payload
R=Path(__file__).resolve().parents[2]/'demo-data'
def record(key,value,time,version=1,status='final'):
 d=payload();a=d['asset'];f=d['fact'];e=d['anchor'];aid='asset_'+key;fid='fact_'+key
 a.update(asset_id=aid,asset_version_id=f'{aid}_v{version}',version=version,supersedes_asset_version_id=f'{aid}_v{version-1}' if version>1 else None,record_status=status)
 a['source']['record_key']='record_'+key
 e.update(anchor_id=f'anchor_{key}_v{version}',asset_version_id=a['asset_version_id']);e['locator']['record_key']=a['source']['record_key']
 f.update(fact_id=fid,fact_version_id=f'{fid}_v{version}',version=version,supersedes_fact_version_id=f'{fid}_v{version-1}' if version>1 else None,anchor_ids=[e['anchor_id']],record_status=status)
 f['event_time']['value']=time;f['value'].update(raw_value=value,value=value)
 d['source_record']={'result_value':value,'unit':'μmol/L','specimen':'serum','specimen_time':time,'report_status':status}
 return d
if __name__=='__main__':
 R.mkdir(exist_ok=True)
 one=record('visit_a','86','2026-09-27T08:00:00+08:00');two=record('visit_b','92','2026-09-29T09:00:00+08:00');fix=record('visit_b','90','2026-09-29T09:00:00+08:00',2,'corrected');cancel=record('visit_b','90','2026-09-29T09:00:00+08:00',3,'cancelled')
 for name,d in [('01-one-result',one),('02-two-results',[one,two]),('03-corrected',fix),('04-cancelled',cancel)]:
  (R/(name+'.json')).write_text(json.dumps(d,ensure_ascii=False,indent=2))
