from __future__ import annotations

import httpx

from app.services import model_settings as ms
from app.services.embedding import embed as local_embed


class VectorProvider:
    def __init__(self):
        self._model = None
        self._loaded_name: str | None = None

    @property
    def mode(self) -> str:
        return ms.effective().embedding.provider

    def _load_bge(self, model_name: str):
        if self._model is None or self._loaded_name != model_name:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(model_name)
            self._loaded_name = model_name
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        cfg = ms.effective().embedding
        provider = (cfg.provider or "local").lower()
        if provider == "bge":
            model = self._load_bge(cfg.model or "BAAI/bge-m3")
            return model.encode(texts, normalize_embeddings=True).tolist()
        if provider == "openai_compatible":
            return self._embed_openai(texts, cfg)
        return [local_embed(t) for t in texts]

    def _embed_openai(self, texts: list[str], cfg) -> list[list[float]]:
        if not cfg.base_url:
            raise ValueError("embedding.base_url required for openai_compatible")
        url = cfg.base_url.rstrip("/") + "/embeddings"
        headers = {"Content-Type": "application/json"}
        if cfg.api_key:
            headers["Authorization"] = f"Bearer {cfg.api_key}"
        payload = {"model": cfg.model or "text-embedding-3-small", "input": texts}
        with httpx.Client(timeout=30, trust_env=False) as c:
            r = c.post(url, headers=headers, json=payload)
            r.raise_for_status()
        data = r.json()["data"]
        data = sorted(data, key=lambda x: x.get("index", 0))
        return [row["embedding"] for row in data]

    async def test_embed(self) -> dict:
        try:
            vecs = self.embed(["kee connectivity probe"])
            return {
                "ok": True,
                "provider": self.mode,
                "dims": len(vecs[0]) if vecs else 0,
            }
        except Exception as e:
            return {"ok": False, "error": f"{type(e).__name__}: {e}", "provider": self.mode}


vector_provider = VectorProvider()
