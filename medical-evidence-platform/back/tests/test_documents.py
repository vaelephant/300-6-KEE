import io,base64
from reportlab.pdfgen import canvas
from tests.test_api import client,H

def pdf(text=True):
 b=io.BytesIO();c=canvas.Canvas(b)
 if text:c.drawString(60,750,'Synthetic report - Creatinine: 86 umol/L')
 else:c.rect(60,700,100,20)
 c.showPage();c.save();return b.getvalue()
def upload(c,data):return c.post('/v1/documents/import',headers=H,json={'patient_id':'patient_demo','filename':'demo.pdf','content_base64':base64.b64encode(data).decode()})
def test_pdf_cycle():
 c=client();r=upload(c,pdf());assert r.status_code==200,r.text
 av=r.json()['asset_version_id'];assert r.json()['status']=='text_extracted'
 r=c.post('/v1/documents/search',headers=H,json={'patient_id':'patient_demo','query':'Creatinine'})
 hit=r.json()['items'][0];assert hit['page']==1 and hit['locator']['width']>0
 r=c.get(f'/v1/documents/{av}/pages/1',headers=H);assert r.status_code==200 and r.content.startswith(b'\x89PNG')
 assert c.get(f'/v1/documents/{av}/pages/2',headers=H).status_code==422
 assert c.get(f'/v1/documents/{av}/pages/1').status_code in (401,403)
def test_no_text_and_invalid():
 c=client();assert upload(c,pdf(False)).json()['status']=='needs_ocr'
 assert upload(c,b'not a pdf').status_code==422
 assert c.post('/v1/documents/search',headers=H,json={'patient_id':'other','query':'Creatinine'}).status_code==403

def test_document_dedup_and_listing():
 c=client();data=pdf();a=upload(c,data).json();b=upload(c,data).json()
 assert a['import_status']=='created' and b['import_status']=='unchanged'
 assert a['asset_version_id']==b['asset_version_id']
 r=c.post('/v1/documents/list',headers=H,json={'patient_id':'patient_demo','limit':1}).json()
 assert len(r['items'])==1 and r['next_offset'] is None
 assert r['items'][0]['asset_version_id']==a['asset_version_id']
 assert c.post('/v1/documents/list',headers=H,json={'patient_id':'other'}).status_code==403

def test_document_pagination_and_no_text_browse():
 c=client();upload(c,pdf());blank=upload(c,pdf(False)).json()
 r=c.post('/v1/documents/list',headers=H,json={'patient_id':'patient_demo','limit':1}).json()
 assert r['next_offset']==1
 r2=c.post('/v1/documents/list',headers=H,json={'patient_id':'patient_demo','limit':1,'offset':1}).json()
 assert r2['items'][0]['asset_version_id']!=r['items'][0]['asset_version_id']
 assert c.get('/v1/documents/'+blank['asset_version_id']+'/pages/1',headers=H).status_code==200

def test_scanned_pdf_ocr():
 from PIL import Image,ImageDraw,ImageFont
 from reportlab.lib.utils import ImageReader
 im=Image.new('RGB',(1200,300),'white');draw=ImageDraw.Draw(im)
 font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',40)
 draw.text((40,70),'Creatinine 86 umol/L',font=font,fill='black')
 b=io.BytesIO();page=canvas.Canvas(b,pagesize=(600,150));page.drawImage(ImageReader(im),0,0,width=600,height=150);page.showPage();page.save()
 c=client();data=upload(c,b.getvalue()).json();assert data['status']=='needs_ocr'
 av=data['asset_version_id'];r=c.post('/v1/documents/ocr',headers=H,json={'asset_version_id':av,'language':'eng'})
 assert r.status_code==200,r.text
 assert r.json()['block_count']>0 and r.json()['review_status']=='unreviewed'
 hits=c.post('/v1/documents/search',headers=H,json={'patient_id':'patient_demo','query':'Creatinine'}).json()['items']
 assert hits and hits[0]['extraction_method']=='ocr'
 assert c.post('/v1/documents/ocr',headers=H,json={'asset_version_id':av,'language':'eng'}).json()['status']=='unchanged'
 assert c.post('/v1/documents/ocr',headers=H,json={'asset_version_id':av,'language':'definitely_missing'}).status_code==422
 assert c.post('/v1/documents/ocr',json={'asset_version_id':av}).status_code in (401,403)
