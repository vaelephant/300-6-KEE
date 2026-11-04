from tests.test_api import client,H
from app.demo import payload
from tests.test_documents import upload,pdf

def ask(c,**kw):
 return c.post('/v1/assistant/ask',headers=H,json={'patient_id':'patient_demo','question':'最近两次肌酐',**kw})
def test_demo_snapshot_and_scope():
 c=client();c.post('/v1/ingestion/lab-records',headers=H,json=payload())
 r=ask(c);assert r.status_code==200,r.text
 b=r.json();assert b['mode']=='demo' and b['statements'][0]['evidence_ids']==['anchor_1']
 assert c.get('/v1/assistant/answers/'+b['answer_id'],headers=H).json()==b
 assert ask(c,patient_id='other').status_code==403
 assert ask(client([])).status_code==403
 assert ask(c,question=' ').status_code==422

def test_document_and_empty():
 c=client();assert ask(c).json()['empty_message']
 upload(c,pdf());b=ask(c,question='Synthetic').json()
 assert b['evidence'][0]['kind']=='document'
 assert b['evidence'][0]['page']==1

def test_model_citations_and_injection(monkeypatch):
 from app import answering
 c=client();c.post('/v1/ingestion/lab-records',headers=H,json=payload())
 def fake(messages,tools=None):
  if tools:return {'tool_calls':[{'id':'call_1','type':'function','function':{'name':'query_lab_results','arguments':'{}'}}]}
  return {'content':'{"statements":[{"text":"fabricated","evidence_ids":["fake_id"]}]}'}
 monkeypatch.setattr(answering,'completion',fake)
 b=ask(c,mode='model').json();assert b['status']=='evidence_fallback';assert 'fabricated' not in str(b)
 def malicious(messages,tools=None):return {'tool_calls':[{'id':'1','function':{'name':'query_lab_results','arguments':'{"patient_id":"other"}'}}]}
 monkeypatch.setattr(answering,'completion',malicious)
 assert ask(c,mode='model').status_code==422

def test_real_adapter_contract(monkeypatch):
 from app import answering
 c=client();c.post('/v1/ingestion/lab-records',headers=H,json=payload())
 def fake(messages,tools=None):
  if tools:return {'tool_calls':[{'id':'call_1','type':'function','function':{'name':'query_lab_results','arguments':'{}'}}]}
  assert messages[-1]['role']=='tool'
  return {'content':'{"statements":[{"text":"肌酐为86 μmol/L","evidence_ids":["anchor_1"]}]}'}
 monkeypatch.setattr(answering,'completion',fake)
 b=ask(c,mode='model').json();assert b['status']=='citation_checked'
