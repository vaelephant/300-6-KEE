import threading
OCR_LOCK=threading.Lock()
import base64,binascii
from fastapi import Depends,HTTPException,Response
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from . import models as m
from .documents import import_pdf,page_png,existing_import
class Upload(BaseModel):
 model_config=ConfigDict(extra='forbid')
 patient_id:str
 encounter_id:str|None=None
 filename:str=Field(min_length=1,max_length=128)
 content_base64:str=Field(max_length=7*1024*1024)
class OCRRequest(BaseModel):
 model_config=ConfigDict(extra='forbid')
 asset_version_id:str
 language:str=Field(default='eng',max_length=64)
class Search(BaseModel):
 model_config=ConfigDict(extra='forbid')
 patient_id:str
 query:str=Field(min_length=1,max_length=100)
 include_rejected:bool=False
 reviewed_only:bool=False
class ListRequest(BaseModel):
 model_config=ConfigDict(extra='forbid')
 patient_id:str
 offset:int=Field(default=0,ge=0)
 limit:int=Field(default=20,ge=1,le=100)
def attach(app,engine,auth,allow):
 @app.post('/v1/documents/ocr')
 def ocr(body:OCRRequest,p=Depends(auth)):
  from .ocr import run
  from .repository import Repository
  # A process-wide lock bounds demo OCR concurrency; use a queue in production.
  if not OCR_LOCK.acquire(blocking=False):raise HTTPException(409,'OCR正在运行，请稍后重试')
  try:
   with engine.begin() as c:
    doc=Repository(c,p['tenant_id']).get(m.document_files,'asset_version_id',body.asset_version_id)
    if not doc:raise HTTPException(404,'Document not found')
    allow(p,doc['patient_id'],'ingest')
    return run(c,p['tenant_id'],body.asset_version_id,body.language)
  except ValueError as e:raise HTTPException(422,str(e))
  finally:OCR_LOCK.release()

 @app.post('/v1/documents/list')
 def listing(body:ListRequest,p=Depends(auth)):
  allow(p,body.patient_id,'read')
  with engine.begin() as c:
   f=m.document_files;a=m.asset_versions
   rows=c.execute(select(f.c.asset_version_id,f.c.filename,f.c.page_count,f.c.status,a.c.payload).join(a,(f.c.tenant_id==a.c.tenant_id)&(f.c.asset_version_id==a.c.asset_version_id)).where(f.c.tenant_id==p['tenant_id'],f.c.patient_id==body.patient_id).order_by(f.c.asset_version_id).offset(body.offset).limit(body.limit+1)).mappings().all()
   return {'items':[{'asset_version_id':r['asset_version_id'],'filename':r['filename'],'page_count':r['page_count'],'status':r['status'],'ingested_at':r['payload']['ingested_at'],'encounter_id':r['payload']['scope']['encounter_id']} for r in rows[:body.limit]],'next_offset':body.offset+body.limit if len(rows)>body.limit else None}

 @app.post('/v1/documents/import')
 def upload(body:Upload,p=Depends(auth)):
  allow(p,body.patient_id,'ingest')
  try:
   data=base64.b64decode(body.content_base64,validate=True)
   with engine.begin() as c:return import_pdf(c,p['tenant_id'],{'patient_id':body.patient_id,'encounter_id':body.encounter_id},body.filename,data)
  except IntegrityError:
   with engine.begin() as c:
    previous=existing_import(c,p['tenant_id'],{'patient_id':body.patient_id,'encounter_id':body.encounter_id},data)
   if previous:return previous
   raise HTTPException(422,'患者或就诊关联无效')
  except (ValueError,binascii.Error):raise HTTPException(422,'PDF无效、范围不匹配或暂不支持该版面；上限5MB/50页')
  except Exception:raise HTTPException(422,'PDF解析失败，未导入')
 @app.post('/v1/documents/search')
 def search(body:Search,p=Depends(auth)):
  allow(p,body.patient_id,'read')
  if not body.query.strip():raise HTTPException(422,'请输入关键词')
  with engine.begin() as c:
   from .reviews import latest
   # Development implementation: filters reviewed text before applying result limit.
   candidates=c.execute(select(m.document_blocks).where(m.document_blocks.c.tenant_id==p['tenant_id'],m.document_blocks.c.patient_id==body.patient_id).order_by(m.document_blocks.c.asset_version_id,m.document_blocks.c.page,m.document_blocks.c.anchor_id)).mappings()
   items=[]
   for row in candidates:
    review=latest(c,p['tenant_id'],row['anchor_id'])
    decision=review['decision'] if review else 'unreviewed'
    if decision=='rejected' and not body.include_rejected:continue
    if body.reviewed_only and decision not in ('confirmed','corrected'):continue
    text=review['reviewed_text'] if review and decision=='corrected' else row['text']
    if body.query.strip().casefold() not in text.casefold():continue
    a=c.execute(select(m.anchors.c.payload).where(m.anchors.c.tenant_id==p['tenant_id'],m.anchors.c.anchor_id==row['anchor_id'])).scalar_one()
    items.append({'anchor_id':row['anchor_id'],'asset_version_id':row['asset_version_id'],'page':row['page'],'text':text,'original_text':row['text'],'locator':a['locator'],'extraction_method':'ocr' if a['locator']['representation_version_id'].startswith('ocr_') else 'pdf_text','review_status':decision,'review_revision':review['revision'] if review else 0})
    if len(items)>100:break
   return {'items':items[:100],'truncated':len(items)>100,'coverage':'按有效审核文字匹配；默认排除已驳回结果。无文字页面和未OCR部分不在检索范围。'}
 @app.get('/v1/documents/{asset_version_id}/pages/{page}')
 def page(asset_version_id:str,page:int,p=Depends(auth)):
  with engine.begin() as c:
   row=c.execute(select(m.document_files).where(m.document_files.c.tenant_id==p['tenant_id'],m.document_files.c.asset_version_id==asset_version_id)).mappings().one_or_none()
   if not row:raise HTTPException(404,'Document not found')
   allow(p,row['patient_id'],'read')
   try:return Response(page_png(row['data'],page),media_type='image/png',headers={'Cache-Control':'no-store'})
   except Exception:raise HTTPException(422,'Page cannot be rendered')

 return search
