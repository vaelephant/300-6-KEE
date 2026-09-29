import json
import httpx

from app.services import model_settings as ms


def _normalize_base(url: str) -> str:
    return (url or "").rstrip("/")


def _ollama_root(base: str) -> str | None:
    """http://host:11434/v1 → http://host:11434"""
    b = _normalize_base(base)
    if not b:
        return None
    if b.endswith("/v1"):
        return b[:-3]
    return None


class AIProvider:
    async def extract(self, text: str) -> dict | None:
        cfg = ms.effective().llm
        # Ollama often works with any/empty key
        if not (cfg.base_url and cfg.model):
            return None
        if not cfg.api_key and "11434" not in cfg.base_url and "ollama" not in cfg.base_url.lower():
            return None
        url = _normalize_base(cfg.base_url) + "/chat/completions"
        prompt = (
            "Extract atomic knowledge from the text. Return ONLY JSON with keys claims "
            "(array of strings), entities (array of strings), relations (array of objects "
            "with source, predicate, target). Keep facts grounded in input; do not invent. Text:\n"
            + text[:12000]
        )
        headers = {"Content-Type": "application/json"}
        if cfg.api_key:
            headers["Authorization"] = f"Bearer {cfg.api_key}"
        payload = {
            "model": cfg.model,
            "messages": [
                {"role": "system", "content": "You are a precise knowledge extraction engine."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=45, trust_env=False) as c:
            r = await c.post(url, headers=headers, json=payload)
            r.raise_for_status()
        raw = r.json()["choices"][0]["message"]["content"]
        try:
            return json.loads(raw)
        except Exception:
            return None

    async def list_models(self, base_url: str | None = None, api_key: str | None = None) -> dict:
        """List models via OpenAI /models, with Ollama /api/tags fallback.

        Uses trust_env=False so system HTTP_PROXY cannot 502 localhost Ollama.
        """
        cfg = ms.effective().llm
        base = _normalize_base(base_url if base_url is not None else cfg.base_url)
        key = api_key if api_key not in (None, "") else cfg.api_key
        if not base:
            return {"ok": False, "error": "base_url required", "models": []}

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"

        errors: list[str] = []
        async with httpx.AsyncClient(timeout=20, trust_env=False) as c:
            # 1) OpenAI-compatible
            url = base + "/models"
            try:
                r = await c.get(url, headers=headers)
                r.raise_for_status()
                data = r.json()
                items = data.get("data") if isinstance(data, dict) else data
                if isinstance(items, list):
                    ids = self._ids_from_openai(items)
                    return {"ok": True, "models": ids, "count": len(ids), "source": url}
                errors.append("unexpected /models payload")
            except Exception as e:
                errors.append(f"/models: {type(e).__name__}: {e}")

            # 2) Ollama native
            root = _ollama_root(base) or base
            tags_url = root.rstrip("/") + "/api/tags"
            try:
                r = await c.get(tags_url)
                r.raise_for_status()
                data = r.json()
                models = data.get("models") if isinstance(data, dict) else None
                if isinstance(models, list):
                    ids = sorted(
                        {
                            str(m.get("name") or m.get("model"))
                            for m in models
                            if isinstance(m, dict) and (m.get("name") or m.get("model"))
                        },
                        key=str.lower,
                    )
                    return {"ok": True, "models": ids, "count": len(ids), "source": tags_url}
                errors.append("unexpected /api/tags payload")
            except Exception as e:
                errors.append(f"/api/tags: {type(e).__name__}: {e}")

        return {
            "ok": False,
            "error": "; ".join(errors)
            + " — if using a system proxy, KEE now bypasses it for model calls; restart API if still failing",
            "models": [],
        }

    @staticmethod
    def _ids_from_openai(items: list) -> list[str]:
        ids: list[str] = []
        for row in items:
            if isinstance(row, str):
                ids.append(row)
            elif isinstance(row, dict) and row.get("id"):
                ids.append(str(row["id"]))
        return sorted(set(ids), key=str.lower)

    async def test_chat(self) -> dict:
        cfg = ms.effective().llm
        if not (cfg.base_url and cfg.model):
            return {"ok": False, "error": "llm base_url / model not set"}
        url = _normalize_base(cfg.base_url) + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        if cfg.api_key:
            headers["Authorization"] = f"Bearer {cfg.api_key}"
        payload = {
            "model": cfg.model,
            "messages": [{"role": "user", "content": "Reply with the single word: pong"}],
            "temperature": 0,
            "max_tokens": 16,
        }
        try:
            async with httpx.AsyncClient(timeout=20, trust_env=False) as c:
                r = await c.post(url, headers=headers, json=payload)
                r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            return {"ok": True, "reply": (content or "")[:200]}
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}


ai_provider = AIProvider()
