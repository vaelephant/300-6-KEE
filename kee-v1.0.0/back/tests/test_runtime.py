from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_runtime_context():
    client.post(
        "/api/v1/knowledge/evolve",
        json={
            "content": "KEE runtime test knowledge supports grounded context.",
            "source": "official-test",
            "domain": "general",
            "auto_promote": True,
        },
    )
    r = client.post(
        "/api/v1/runtime/context",
        json={"question": "What supports grounded context?", "top_k": 4, "min_trust": 0},
    )
    assert r.status_code == 200
    d = r.json()
    assert "citations" in d and "context" in d and d["grounded"] is True


def test_agent_protocol():
    r = client.post("/api/v1/runtime/agent", json={"question": "grounded context", "min_trust": 0})
    assert r.status_code == 200
    body = r.json()
    assert body["protocol"] == "kee-agent-context/1.0"
    assert "instructions" in body
    assert "context_pack" in body
    assert "grounded" in body["context_pack"]
    assert "citations" in body["context_pack"]
