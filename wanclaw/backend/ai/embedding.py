import httpx
import logging
import os
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class EmbeddingService:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "nomic-embed-text"):
        self.base_url = base_url
        self.model = model
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def embed(self, text: str) -> List[float]:
        try:
            client = await self._get_client()
            resp = await client.post("/api/embeddings", json={"model": self.model, "prompt": text})
            if resp.status_code == 200:
                return resp.json().get("embedding", [])
        except Exception as e:
            logger.warning(f"Embedding request failed: {e}")
        return []

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        results = []
        for text in texts:
            emb = await self.embed(text)
            results.append(emb)
        return results

    async def is_available(self) -> bool:
        try:
            client = await self._get_client()
            resp = await client.get("/api/tags")
            return resp.status_code == 200
        except Exception:
            return False


_emb_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    global _emb_service
    if _emb_service is None:
        _emb_service = EmbeddingService()
    return _emb_service


class SemanticMemoryLayer:
    def __init__(self, memory_layer, embedding_service: EmbeddingService = None):
        self._layer = memory_layer
        self._emb = embedding_service

    async def add_with_embedding(self, content: str, tags: List[str] = None, source: str = ""):
        import time
        embedding = []
        if self._emb:
            try:
                embedding = await self._emb.embed(content)
            except Exception:
                pass
        entry = {
            "content": content,
            "tags": tags or [],
            "timestamp": time.time(),
            "source": source,
        }
        if embedding:
            entry["embedding"] = embedding
        self._layer.append_jsonl(entry)
        self._layer.write_md(
            self._layer.name.capitalize(),
            content,
            section=f"Entry {int(time.time())}"
        )

    async def search_by_embedding(self, query_embedding: List[float], top_k: int = 5) -> List[Dict]:
        results = []
        entries = self._layer.read_jsonl(500)
        for entry in entries:
            emb = entry.get("embedding")
            if not emb:
                continue
            score = cosine_similarity(query_embedding, emb)
            if score > 0.5:
                results.append({**entry, "similarity": round(score, 4)})
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    async def search_text(self, query_text: str, top_k: int = 5) -> List[Dict]:
        if not self._emb:
            return []
        try:
            query_emb = await self._emb.embed(query_text)
            return await self.search_by_embedding(query_emb, top_k)
        except Exception:
            return []
