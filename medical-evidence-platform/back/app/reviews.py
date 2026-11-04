import uuid
from typing import Literal
from fastapi import Depends,HTTPException
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import select,insert
from sqlalchemy.exc import IntegrityError
from . import models as m
from .service import now
class Review(BaseModel):
 model_config=ConfigDict(extra='forbid')
 anchor_id:str
 expected_revision:int=Field(ge=0)
 decision:Literal['confirmed','corrected','rejected']
 text:str=Field(default='',max_length=10000)
 reason:str=Field(min_length=1,max_length=1000)
class QueueRequest(BaseModel):
 model_config=ConfigDict(extra='forbid')
 patient_id:str
 status:Literal['unreviewed','confirmed','corrected','rejected','all']='unreviewed'
 offset:int=Field(default=0,ge=0)
 limit:int=Field(default=20,ge=1,le=100)
def latest(c,tenant,anchor):
 return c.execute(select(m.ocr_reviews).where(m.ocr_reviews.c.tenant_id==tenant,m.ocr_reviews.c.anchor_id==anchor).order_by(m.ocr_reviews.c.revision.desc()).limit(1)).mappings().first()
def attach(app,engine,auth,allow):
 @app.post('/v1/documents/review-queue')
 def queue(body:QueueRequest,p=Depends(auth)):
  allow(p,body.patient_id,'read')
  with engine.begin() as c:
   b=m.document_blocks;a=m.anchors
   rows=c.execute(select(b.c.anchor_id,b.c.asset_version_id,b.c.page,b.c.text,a.c.payload).join(a,(b.c.tenant_id==a.c.tenant_id)&(b.c.anchor_id==a.c.anchor_id)).where(b.c.tenant_id==p['tenant_id'],b.c.patient_id==body.patient_id).order_by(b.c.asset_version_id,b.c.page,b.c.anchor_id)).mappings()
   items=[];matched=0
   for row in rows:
    loc=row['payload']['locator']
    if not loc.get('representation_version_id','').startswith('ocr_'):continue
    rev=latest(c,p['tenant_id'],row['anchor_id']);status=rev['decision'] if rev else 'unreviewed'
    if body.status!='all' and status!=body.status:continue
    matched+=1
    if matched<=body.offset:continue
    items.append({'anchor_id':row['anchor_id'],'asset_version_id':row['asset_version_id'],'page':row['page'],'text':rev['reviewed_text'] if rev and status=='corrected' else row['text'],'original_text':row['text'],'locator':loc,'extraction_method':'ocr','review_status':status,'review_revision':rev['revision'] if rev else 0})
    if len(items)>body.limit:break
   return {'items':items[:body.limit],'next_offset':body.offset+body.limit if len(items)>body.limit else None}

 def target(c,p,aid,permission):
  a=c.execute(select(m.anchors).where(m.anchors.c.tenant_id==p['tenant_id'],m.anchors.c.anchor_id==aid)).mappings().first()
  if not a:raise HTTPException(404,'Evidence not found')
  allow(p,a['patient_id'],permission)
  if not a['payload']['locator'].get('representation_version_id','').startswith('ocr_'):raise HTTPException(422,'Only OCR evidence can be reviewed')
  return a
 @app.post('/v1/documents/reviews')
 def review(body:Review,p=Depends(auth)):
  try:
   with engine.begin() as c:
    target(c,p,body.anchor_id,'review');old=latest(c,p['tenant_id'],body.anchor_id)
    rev=old['revision'] if old else 0
    if rev!=body.expected_revision:raise HTTPException(409,'审核记录已更新，请重新打开证据')
    original=c.execute(select(m.document_blocks.c.text).where(m.document_blocks.c.tenant_id==p['tenant_id'],m.document_blocks.c.anchor_id==body.anchor_id)).scalar_one()
    text=body.text.strip() if body.decision=='corrected' else original
    if body.decision=='corrected' and not text:raise HTTPException(422,'纠正后的文字不能为空')
    if not body.reason.strip():raise HTTPException(422,'请输入审核说明')
    row={'tenant_id':p['tenant_id'],'review_id':'review_'+uuid.uuid4().hex,'anchor_id':body.anchor_id,'revision':rev+1,'decision':body.decision,'reviewed_text':text,'actor_id':p['actor_id'],'created_at':now(),'reason':body.reason.strip()}
    c.execute(insert(m.ocr_reviews).values(**row));return row
  except IntegrityError:raise HTTPException(409,'并发审核冲突，请刷新')
 @app.get('/v1/documents/reviews/{anchor_id}')
 def history(anchor_id:str,p=Depends(auth)):
  with engine.begin() as c:
   target(c,p,anchor_id,'read')
   rows=c.execute(select(m.ocr_reviews).where(m.ocr_reviews.c.tenant_id==p['tenant_id'],m.ocr_reviews.c.anchor_id==anchor_id).order_by(m.ocr_reviews.c.revision.desc())).mappings().all()
   return {'items':[dict(r) for r in rows],'revision':rows[0]['revision'] if rows else 0}
