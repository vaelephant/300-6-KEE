import base64,hashlib,io,uuid,json
import pdfplumber
import pypdfium2 as pdfium
from sqlalchemy import insert,select,func
from . import models as m
from .repository import Repository
from .service import now

def parse_pdf(data):
 if len(data)>5*1024*1024 or not data.startswith(b'%PDF-'):raise ValueError('PDF required, maximum 5MB')
 blocks=[];empty=[]
 with pdfplumber.open(io.BytesIO(data)) as pdf:
  if not 1<=len(pdf.pages)<=50:raise ValueError('PDF must have 1-50 pages')
  for i,page in enumerate(pdf.pages,1):
   if page.rotation:raise ValueError('Rotated PDF pages are not supported yet')
   if page.cropbox and tuple(page.cropbox)!=tuple(page.mediabox):raise ValueError('Cropped page geometry is not supported yet')
   words=page.extract_words()
   if not words:empty.append(i)
   # one line per evidence block, using source word coordinates
   lines=[]
   for w in words:
    if not lines or abs(lines[-1][0]['top']-w['top'])>3:lines.append([w])
    else:lines[-1].append(w)
   for line in lines:
    x0=min(w['x0'] for w in line)/page.width;y0=min(w['top'] for w in line)/page.height
    x1=max(w['x1'] for w in line)/page.width;y1=max(w['bottom'] for w in line)/page.height
    if not 0<=x0<x1<=1 or not 0<=y0<y1<=1:raise ValueError('Unsupported page geometry')
    blocks.append((i,' '.join(w['text'] for w in line),x0,y0,x1-x0,y1-y0))
  return len(pdf.pages),blocks,empty

def import_key(scope,data):
 return hashlib.sha256(json.dumps([scope['patient_id'],scope['encounter_id'],hashlib.sha256(data).hexdigest()],ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def existing_import(c,tenant,scope,data):
 av=c.execute(select(m.document_import_keys.c.asset_version_id).where(m.document_import_keys.c.tenant_id==tenant,m.document_import_keys.c.import_key==import_key(scope,data))).scalar_one_or_none()
 if not av:return None
 row=c.execute(select(m.document_files).where(m.document_files.c.tenant_id==tenant,m.document_files.c.asset_version_id==av)).mappings().one()
 pages=set(c.execute(select(m.document_blocks.c.page).where(m.document_blocks.c.tenant_id==tenant,m.document_blocks.c.asset_version_id==av)).scalars())
 count=c.execute(select(func.count()).select_from(m.document_blocks).where(m.document_blocks.c.tenant_id==tenant,m.document_blocks.c.asset_version_id==av)).scalar_one()
 return {'asset_version_id':av,'page_count':row['page_count'],'block_count':count,'status':row['status'],'pages_without_text':[i for i in range(1,row['page_count']+1) if i not in pages],'import_status':'unchanged'}

def import_pdf(c,tenant,scope,filename,data):
 previous=existing_import(c,tenant,scope,data)
 if previous:return previous
 pages,blocks,empty=parse_pdf(data);r=Repository(c,tenant);key=uuid.uuid4().hex;av='pdfv_'+key
 a={'schema_version':'1.0.0','tenant_id':tenant,'asset_id':'pdf_'+key,'asset_version_id':av,'version':1,'scope':scope,'modality':'pdf','source':{'system_id':'manual_pdf','record_key':key,'source_version':None,'history_completeness':'snapshot_only'},'content':{'object_key':'db:'+av,'sha256':hashlib.sha256(data).hexdigest(),'media_type':'application/pdf','size_bytes':len(data)},'record_status':'unknown','ingested_at':now(),'supersedes_asset_version_id':None}
 r.add_asset(a)
 for i,text,x,y,w,h in blocks:
  aid='pdfanchor_'+uuid.uuid4().hex
  anchor={'schema_version':'1.0.0','tenant_id':tenant,'anchor_id':aid,'asset_version_id':av,'locator':{'kind':'page_region','page':i,'x':x,'y':y,'width':w,'height':h,'coordinate_system':'normalized_top_left','representation_version_id':av+':pdfplumber:'+pdfplumber.__version__},'created_at':now()}
  r.add_anchor(anchor)
  c.execute(insert(m.document_blocks).values(tenant_id=tenant,anchor_id=aid,patient_id=scope['patient_id'],asset_version_id=av,page=i,text=text))
 status='needs_ocr' if not blocks else ('partial_text' if empty else 'text_extracted')
 c.execute(insert(m.document_files).values(tenant_id=tenant,asset_version_id=av,patient_id=scope['patient_id'],filename=filename,data=data,page_count=pages,status=status))
 c.execute(insert(m.document_import_keys).values(tenant_id=tenant,import_key=import_key(scope,data),asset_version_id=av))
 return {'import_status':'created','asset_version_id':av,'page_count':pages,'block_count':len(blocks),'status':status,'pages_without_text':empty}

def page_png(data,number):
 doc=pdfium.PdfDocument(data)
 try:
  if number<1 or number>len(doc):raise ValueError('Invalid page')
  page=doc[number-1]
  try:
   w,h=page.get_size();scale=min(1.5,1800/max(w,h));bitmap=page.render(scale=scale)
   try:
    image=bitmap.to_pil();buf=io.BytesIO();image.save(buf,format='PNG');return buf.getvalue()
   finally:bitmap.close()
  finally:page.close()
 finally:doc.close()
