"""Explicit OCR of pages without extracted text. No clinical fact generation."""
import csv,io,subprocess,tempfile,uuid,re,time
from pathlib import Path
from sqlalchemy import select,insert,update
from . import models as m
from .documents import page_png
from .repository import Repository
from .service import now

def engine_info(language):
 if not re.fullmatch(r'[a-z_]+(?:\+[a-z_]+)*',language):raise ValueError('Invalid OCR language')
 try:
  version=subprocess.run(['tesseract','--version'],capture_output=True,text=True,timeout=5,check=True).stdout.splitlines()[0]
  langs=subprocess.run(['tesseract','--list-langs'],capture_output=True,text=True,timeout=5,check=True).stdout.splitlines()[1:]
 except (OSError,subprocess.SubprocessError):raise ValueError('Tesseract unavailable')
 if not set(language.split('+')).issubset(set(langs)):raise ValueError('Missing Tesseract language pack: '+language)
 return version

def recognize(png,language):
 from PIL import Image
 with Image.open(io.BytesIO(png)) as im:w,h=im.size
 with tempfile.TemporaryDirectory(prefix='evidence-ocr-') as folder:
  file=Path(folder)/'page.png';file.write_bytes(png)
  try:r=subprocess.run(['tesseract',str(file),'stdout','-l',language,'--psm','6','tsv'],capture_output=True,text=True,timeout=40,check=True)
  except subprocess.SubprocessError:raise ValueError('OCR failed or timed out')
 groups={}
 for row in csv.DictReader(io.StringIO(r.stdout),delimiter='\t'):
  if row.get('level')!='5' or not row.get('text','').strip():continue
  key=(row['block_num'],row['par_num'],row['line_num']);groups.setdefault(key,[]).append(row)
 result=[]
 for words in groups.values():
  left=min(int(t['left']) for t in words);top=min(int(t['top']) for t in words)
  right=max(int(t['left'])+int(t['width']) for t in words);bottom=max(int(t['top'])+int(t['height']) for t in words)
  if not 0<=left<right<=w or not 0<=top<bottom<=h:continue
  result.append({'text':' '.join(t['text'] for t in words),'x':left/w,'y':top/h,'width':(right-left)/w,'height':(bottom-top)/h,'confidence':sum(float(t['conf']) for t in words)/len(words)})
 return result

def run(c,tenant,av,language):
 version=engine_info(language);repo=Repository(c,tenant);doc=repo.get(m.document_files,'asset_version_id',av)
 if not doc:raise ValueError('Document unavailable')
 done=set(c.execute(select(m.document_blocks.c.page).where(m.document_blocks.c.tenant_id==tenant,m.document_blocks.c.asset_version_id==av)).scalars())
 pending=[i for i in range(1,doc['page_count']+1) if i not in done]
 if not pending:return {'status':'unchanged','message':'所有页面已有可检索文字','block_count':0}
 if len(pending)>3:raise ValueError('Demo OCR limited to 3 missing-text pages per document')
 runid='ocr_'+uuid.uuid4().hex;started=now();results=[];begin=time.monotonic()
 for page in pending:
  if time.monotonic()-begin>90:raise ValueError('OCR total processing budget exceeded')
  lines=recognize(page_png(doc['data'],page),language)
  for line in lines:results.append((page,line))
 for page,line in results:
  aid='ocranchor_'+uuid.uuid4().hex
  anchor={'schema_version':'1.0.0','tenant_id':tenant,'anchor_id':aid,'asset_version_id':av,'locator':{'kind':'page_region','page':page,'x':line['x'],'y':line['y'],'width':line['width'],'height':line['height'],'coordinate_system':'normalized_top_left','representation_version_id':runid},'created_at':now()}
  repo.add_anchor(anchor)
  c.execute(insert(m.document_blocks).values(tenant_id=tenant,anchor_id=aid,patient_id=doc['patient_id'],asset_version_id=av,page=page,text=line['text']))
 recognized={p for p,l in results};remaining=[p for p in pending if p not in recognized]
 status='ocr_text_extracted' if not remaining else ('partial_text' if done or recognized else 'needs_ocr')
 payload={'started_at':started,'completed_at':now(),'input_asset_version_id':av,'pages':pending,'pages_without_text':remaining,'block_count':len(results),'review_status':'unreviewed','word_confidence_is_not_truth_probability':True,'lines':[{'page':p,**l} for p,l in results]}
 c.execute(insert(m.document_ocr_runs).values(tenant_id=tenant,run_id=runid,asset_version_id=av,language=language,engine_version=version,status='completed',payload=payload))
 c.execute(update(m.document_files).where(m.document_files.c.tenant_id==tenant,m.document_files.c.asset_version_id==av).values(status=status))
 return {'status':status,'run_id':runid,'block_count':len(results),'pages_without_text':remaining,'review_status':'unreviewed'}
