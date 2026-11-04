from tests.test_api import client,H
from tests.test_documents import pdf,upload

def prepared(monkeypatch,permissions):
 from app import ocr
 monkeypatch.setattr(ocr,'engine_info',lambda lang:'test-engine')
 monkeypatch.setattr(ocr,'recognize',lambda png,lang:[{'text':'Creatinine 86','x':.1,'y':.1,'width':.4,'height':.05,'confidence':90}])
 c=client(permissions);av=upload(c,pdf(False)).json()['asset_version_id']
 assert c.post('/v1/documents/ocr',headers=H,json={'asset_version_id':av}).status_code==200
 hit=c.post('/v1/documents/search',headers=H,json={'patient_id':'patient_demo','query':'Creatinine'}).json()['items'][0]
 return c,hit

def test_review_lifecycle(monkeypatch):
 c,hit=prepared(monkeypatch,['read','ingest','review']);aid=hit['anchor_id']
 def write(rev,decision,text='Creatinine 90'):
  return c.post('/v1/documents/reviews',headers=H,json={'anchor_id':aid,'expected_revision':rev,'decision':decision,'text':text,'reason':'Compared original page'})
 assert write(0,'corrected').status_code==200
 assert write(0,'confirmed').status_code==409
 def search(q,**kwargs):return c.post('/v1/documents/search',headers=H,json={'patient_id':'patient_demo','query':q,**kwargs}).json()['items']
 assert not search('86')
 items=search('90',reviewed_only=True);assert items[0]['original_text']=='Creatinine 86' and items[0]['review_status']=='corrected'
 assert write(1,'rejected').status_code==200
 assert not search('Creatinine')
 assert search('Creatinine',include_rejected=True)[0]['review_status']=='rejected'
 assert write(2,'confirmed').status_code==200
 assert search('86',reviewed_only=True)
 hist=c.get('/v1/documents/reviews/'+aid,headers=H).json();assert [x['revision'] for x in hist['items']]==[3,2,1]

def test_review_permission(monkeypatch):
 c,hit=prepared(monkeypatch,['read','ingest'])
 assert c.post('/v1/documents/reviews',headers=H,json={'anchor_id':hit['anchor_id'],'expected_revision':0,'decision':'confirmed','reason':'check'}).status_code==403

def test_review_queue(monkeypatch):
 c,hit=prepared(monkeypatch,['read','ingest','review'])
 def queue(status):return c.post('/v1/documents/review-queue',headers=H,json={'patient_id':'patient_demo','status':status}).json()['items']
 assert queue('unreviewed')[0]['anchor_id']==hit['anchor_id']
 r=c.post('/v1/documents/reviews',headers=H,json={'anchor_id':hit['anchor_id'],'expected_revision':0,'decision':'confirmed','reason':'verified'})
 assert r.status_code==200 and queue('unreviewed')==[]
 assert queue('confirmed')[0]['review_status']=='confirmed'
 assert c.post('/v1/documents/review-queue',headers=H,json={'patient_id':'other'}).status_code==403
