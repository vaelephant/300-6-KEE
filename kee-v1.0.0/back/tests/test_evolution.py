from fastapi.testclient import TestClient
from app.main import app
from app.repositories.memory import repository

client = TestClient(app)

def setup_function():
    repository.items.clear()

def test_ingest_and_query():
    r = client.post('/api/v1/knowledge/ingest', json={"content":"高血压患者需要定期监测血压。", "source":"guideline", "domain":"medical"})
    assert r.status_code == 200
    q = client.post('/api/v1/knowledge/query', json={"question":"高血压 血压", "domain":"medical"})
    assert q.status_code == 200
    assert len(q.json()["results"]) >= 1

def test_conflict_review_flow():
    first = client.post('/api/v1/knowledge/evolve', json={"content":"A药推荐剂量为10mg。", "source":"guideline-v1", "domain":"medical"}).json()
    assert first["results"][0]["decision"] == "new"
    second = client.post('/api/v1/knowledge/evolve', json={"content":"A药在肾功能不全患者推荐剂量为5mg。", "source":"guideline-v2", "domain":"medical"}).json()
    assert second["results"][0]["decision"] in {"review_required", "reinforced"}
