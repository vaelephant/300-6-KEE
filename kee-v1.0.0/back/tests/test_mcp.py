"""MCP plugin smoke tests (pack shape + kee_get_context tool)."""

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.mcp.mcp_context import mcp_fetch_pack, mcp_pack_text
from app.mcp.mcp_server import kee_get_context

client = TestClient(app)


@pytest.mark.asyncio
async def test_mcp_fetch_pack_shape():
    client.post(
        "/api/v1/knowledge/evolve",
        json={
            "content": "MCP plugin retrieves grounded context for agents.",
            "source": "mcp-test",
            "domain": "general",
            "auto_promote": True,
        },
    )
    pack = await mcp_fetch_pack(question="grounded context for agents", min_trust=0.0)
    assert pack["protocol"] == "kee-agent-context/1.0"
    assert "context_pack" in pack
    assert isinstance(pack["context_pack"]["citations"], list)
    parsed = json.loads(mcp_pack_text(pack))
    assert parsed["protocol"] == "kee-agent-context/1.0"


@pytest.mark.asyncio
async def test_mcp_tool_kee_get_context():
    raw = await kee_get_context(question="grounded context", min_trust=0.0)
    data = json.loads(raw)
    assert data["protocol"] == "kee-agent-context/1.0"
    assert "context_pack" in data
    assert "grounded" in data["context_pack"]
