import asyncio
import httpx

from app.services.ai_provider import AIProvider


def test_list_models_parses_openai_shape(monkeypatch):
    provider = AIProvider()

    class FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"id": "qwen2.5:7b"}, {"id": "llama3.2"}, {"id": "qwen2.5:7b"}]}

    class FakeClient:
        def __init__(self, *a, **k):
            assert k.get("trust_env") is False

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, headers=None):
            assert url.endswith("/models")
            return FakeResp()

    import app.services.ai_provider as mod

    monkeypatch.setattr(mod.httpx, "AsyncClient", FakeClient)
    out = asyncio.run(provider.list_models("http://127.0.0.1:11434/v1", "sk-test"))
    assert out["ok"] is True
    assert out["models"] == ["llama3.2", "qwen2.5:7b"]
    assert out["count"] == 2


def test_list_models_falls_back_to_ollama_tags(monkeypatch):
    provider = AIProvider()

    class TagsResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"models": [{"name": "bge-m3:latest"}, {"name": "qwen2.5:7b-instruct"}]}

    class FakeClient:
        def __init__(self, *a, **k):
            assert k.get("trust_env") is False

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, headers=None):
            if url.endswith("/models"):
                raise httpx.HTTPStatusError(
                    "Server error '502 Bad Gateway'",
                    request=httpx.Request("GET", url),
                    response=httpx.Response(502),
                )
            assert url.endswith("/api/tags")
            return TagsResp()

    import app.services.ai_provider as mod

    monkeypatch.setattr(mod.httpx, "AsyncClient", FakeClient)
    out = asyncio.run(provider.list_models("http://127.0.0.1:11434/v1", ""))
    assert out["ok"] is True
    assert "bge-m3:latest" in out["models"]
    assert out["source"].endswith("/api/tags")
