"""
WanClaw Memory System V2.0

Human-readable memory storage using Markdown files + JSONL transcripts.
Git-backable, no database required. Stateless LLMs act stateful.

Optimizations:
- LRU cache for frequent memory accesses
- BM25 text search indexing for better relevance
- Time-decay priority scoring for memory relevance
- Memory consolidation with token budgeting
- Context window management with truncation
"""

import os
import re
import json
import time
import math
import logging
import hashlib
from typing import Dict, List, Any, Optional, Tuple

from wanclaw.backend.agent.tokenizer import count_tokens
from pathlib import Path
from dataclasses import dataclass, field
from collections import OrderedDict
from threading import RLock

logger = logging.getLogger(__name__)

DEFAULT_MAX_CONTEXT_TOKENS = 8192
DEFAULT_BM25_K1 = 1.5
DEFAULT_BM25_B = 0.75
DEFAULT_DECAY_RATE = 0.995
DEFAULT_MIN_RELEVANCE = 0.3


@dataclass
class MemoryEntry:
    content: str
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    source: str = ""
    access_count: int = 0
    last_access: float = 0.0


class LRUCache:
    def __init__(self, capacity: int = 128):
        self.capacity = capacity
        self._cache: OrderedDict = OrderedDict()
        self._lock = RLock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
        return None

    def put(self, key: str, value: Any):
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            else:
                if len(self._cache) >= self.capacity:
                    self._cache.popitem(last=False)
            self._cache[key] = value

    def clear(self):
        with self._lock:
            self._cache.clear()

    def __len__(self):
        return len(self._cache)


class BM25Indexer:
    def __init__(self, k1: float = DEFAULT_BM25_K1, b: float = DEFAULT_BM25_B):
        self.k1 = k1
        self.b = b
        self._doc_freqs: Dict[str, int] = {}
        self._avgdl = 0.0
        self._doc_lengths: List[int] = []
        self._documents: List[str] = []
        self._doc_ids: List[int] = []

    def _tokenize(self, text: str) -> List[str]:
        text = text.lower()
        tokens = re.findall(r'\w+', text, re.UNICODE)
        return [t for t in tokens if len(t) > 1]

    def add_document(self, doc_id: int, content: str):
        tokens = self._tokenize(content)
        self._documents.append(content)
        self._doc_ids.append(doc_id)
        self._doc_lengths.append(len(tokens))
        for token in set(tokens):
            self._doc_freqs[token] = self._doc_freqs.get(token, 0) + 1

        total_len = sum(self._doc_lengths)
        self._avgdl = total_len / len(self._doc_lengths) if self._doc_lengths else 0

    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        n = len(self._documents)
        doc_scores: Dict[int, float] = {}

        for doc_idx, doc_id in enumerate(self._doc_ids):
            doc_len = self._doc_lengths[doc_idx]
            score = 0.0
            for qt in query_tokens:
                if qt not in self._doc_freqs:
                    continue
                df = self._doc_freqs[qt]
                idf = math.log((n - df + 0.5) / (df + 0.5) + 1)
                tf = sum(1 for t in self._tokenize(self._documents[doc_idx]) if t == qt)
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self._avgdl)
                score += idf * numerator / denominator if denominator else 0
            if score > 0:
                doc_scores[doc_id] = score

        sorted_results = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_results[:top_k]

    def clear(self):
        self._doc_freqs.clear()
        self._doc_lengths.clear()
        self._documents.clear()
        self._doc_ids.clear()
        self._avgdl = 0.0


class MemoryLayer:
    def __init__(self, name: str, base_dir: str, cache_size: int = 64):
        self.name = name
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.md_path = self.base_dir / f"{name}.md"
        self.jsonl_path = self.base_dir / f"{name}.jsonl"
        self._search_cache = LRUCache(capacity=cache_size)
        self._bm25_index = BM25Indexer()
        self._index_built = False
        self._index_lock = RLock()
        self._entry_count = 0

    def write_md(self, title: str, content: str, section: str = None):
        if section:
            if not self.md_path.exists():
                self.md_path.write_text(f"# {self.name}\n\n")
            existing = self.md_path.read_text()
            marker = f"## {section}"
            if marker in existing:
                parts = existing.split(marker)
                end = parts[1].find("\n## ") if "\n## " in parts[1] else len(parts[1])
                existing = parts[0] + marker + f"\n\n{content}\n\n" + parts[1][end:]
                self.md_path.write_text(existing)
            else:
                with open(self.md_path, "a") as f:
                    f.write(f"\n## {section}\n\n{content}\n\n")
        else:
            self.md_path.write_text(f"# {title}\n\n{content}\n\n")

    def read_md(self) -> str:
        if self.md_path.exists():
            return self.md_path.read_text()
        return ""

    def append_jsonl(self, entry: Dict):
        with open(self.jsonl_path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def read_jsonl(self, limit: int = 100) -> List[Dict]:
        if not self.jsonl_path.exists():
            return []
        entries = []
        with open(self.jsonl_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return entries[-limit:]

    def _build_bm25_index(self, entries: List[Dict]):
        with self._index_lock:
            self._bm25_index.clear()
            for idx, entry in enumerate(entries):
                content = entry.get("content", "")
                self._bm25_index.add_document(idx, content)
            self._entry_count = len(entries)
            self._index_built = True

    def search(self, query: str, limit: int = 10, use_bm25: bool = True) -> List[Dict]:
        cache_key = f"{query}:{limit}:{use_bm25}"
        cached = self._search_cache.get(cache_key)
        if cached is not None:
            return cached

        if use_bm25:
            entries = self.read_jsonl(1000)
            if not self._index_built or len(entries) != self._entry_count:
                self._build_bm25_index(entries)

            bm25_scores = self._bm25_index.search(query, limit)
            results = []
            for doc_idx, bm25_score in bm25_scores:
                if doc_idx < len(entries):
                    entry = entries[doc_idx]
                    recency = math.exp(-DEFAULT_DECAY_RATE * (time.time() - entry.get("timestamp", time.time())))
                    access_boost = math.log1p(entry.get("access_count", 0)) * 0.1
                    final_score = bm25_score * (1 + recency * 0.5 + access_boost)
                    results.append({**entry, "search_score": round(final_score, 4), "bm25_score": round(bm25_score, 4)})
            results.sort(key=lambda x: x.get("search_score", 0), reverse=True)
        else:
            query_lower = query.lower()
            results = []
            if self.md_path.exists():
                content = self.md_path.read_text()
                for i, line in enumerate(content.split("\n")):
                    if query_lower in line.lower():
                        results.append({"source": "md", "line": i + 1, "content": line.strip()})
            for entry in self.read_jsonl(500):
                if query_lower in json.dumps(entry, ensure_ascii=False).lower():
                    results.append({"source": "jsonl", "entry": entry})

        self._search_cache.put(cache_key, results[:limit])
        return results[:limit]

    def search_with_embedding(self, query_embedding: List[float], top_k: int = 5) -> List[Dict]:
        from wanclaw.backend.ai.embedding import cosine_similarity
        results = []
        for entry in self.read_jsonl(500):
            emb = entry.get("embedding")
            if not emb:
                continue
            score = cosine_similarity(query_embedding, emb)
            if score > 0.5:
                results.append({**entry, "similarity": round(score, 4)})
        results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        return results[:top_k]


class MemorySystem:
    def __init__(self, base_dir: str = None, max_context_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS):
        self.base_dir = Path(base_dir or os.path.expanduser("~/.wanclaw/memory"))
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.layers: Dict[str, MemoryLayer] = {}
        self.max_context_tokens = max_context_tokens
        self._priority_cache = LRUCache(capacity=256)
        self._init_default_layers()

    def _init_default_layers(self):
        defaults = ["identity", "preferences", "knowledge", "conversations", "tasks"]
        for name in defaults:
            self.layers[name] = MemoryLayer(name, str(self.base_dir))

    def get_layer(self, name: str) -> MemoryLayer:
        if name not in self.layers:
            self.layers[name] = MemoryLayer(name, str(self.base_dir))
        return self.layers[name]

    def remember(self, content: str, category: str = "knowledge", tags: List[str] = None, source: str = ""):
        layer = self.get_layer(category)
        entry = {"content": content, "tags": tags or [], "timestamp": time.time(), "source": source}
        layer.append_jsonl(entry)
        layer.write_md(category.capitalize(), content, section=f"Entry {int(time.time())}")
        logger.info(f"Memory stored: {category} - {content[:50]}")

    def recall(self, query: str, category: str = None, limit: int = 10) -> List[Dict]:
        results = []
        layers = [self.layers[category]] if category and category in self.layers else self.layers.values()
        for layer in layers:
            results.extend(layer.search(query, limit))
        return results[:limit]

    def log_conversation(self, platform: str, user_id: str, role: str, content: str):
        layer = self.get_layer("conversations")
        entry = {"platform": platform, "user_id": user_id, "role": role, "content": content, "time": time.time()}
        layer.append_jsonl(entry)

    def log_task(self, task_name: str, status: str, details: Dict = None):
        layer = self.get_layer("tasks")
        entry = {"task": task_name, "status": status, "details": details or {}, "time": time.time()}
        layer.append_jsonl(entry)

    def get_soul_path(self, account_id: str = None) -> str:
        base = self.base_dir.parent
        if account_id:
            per_account = base / f"SOUL.{account_id}.md"
            if per_account.exists():
                return str(per_account)
        default = base / "SOUL.md"
        if default.exists():
            return str(default)
        return ""

    def load_soul(self, soul_path: str = None, account_id: str = None) -> str:
        if soul_path is None:
            soul_path = self.get_soul_path(account_id)
        if not soul_path:
            return ""
        p = Path(soul_path)
        if p.exists():
            content = p.read_text()
            self.set_identity(content)
            logger.info(f"SOUL.md loaded from {soul_path} (account_id={account_id})")
            return content
        return ""

    def get_identity(self) -> str:
        layer = self.get_layer("identity")
        return layer.read_md() or "# WanClaw Identity\n\nI am WanClaw, a multi-platform AI assistant for SMEs."

    def set_identity(self, identity: str):
        layer = self.get_layer("identity")
        layer.write_md("WanClaw Identity", identity)

    async def semantic_search(self, query: str, account_id: str = None, top_k: int = 5) -> List[Dict]:
        try:
            from wanclaw.backend.ai.embedding import get_embedding_service
            emb_svc = get_embedding_service()
            if not await emb_svc.is_available():
                return self.recall(query, None, top_k)
            query_emb = await emb_svc.embed(query)
            if not query_emb:
                return self.recall(query, None, top_k)
            all_results = []
            for layer in self.layers.values():
                results = layer.search_with_embedding(query_emb, top_k)
                all_results.extend(results)
            all_results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
            return all_results[:top_k]
        except Exception:
            return self.recall(query, None, top_k)

    def flush(self, category: str = None):
        if category:
            layer = self.get_layer(category)
            if layer.jsonl_path.exists():
                layer.jsonl_path.unlink()
                layer._index_built = False
                layer._search_cache.clear()
                logger.info(f"Flushed memory layer: {category}")
        else:
            for name, layer in self.layers.items():
                if layer.jsonl_path.exists():
                    layer.jsonl_path.unlink()
                layer._index_built = False
                layer._search_cache.clear()
            self._priority_cache.clear()
            logger.info("Flushed all memory layers")

    def _estimate_tokens(self, text: str) -> int:
        from wanclaw.backend.agent.tokenizer import count_tokens as _ct
        return _ct(text)

    def _score_by_priority(self, entry: Dict, now: float = None) -> float:
        now = now or time.time()
        timestamp = entry.get("timestamp", now)
        age = now - timestamp
        recency = math.exp(-DEFAULT_DECAY_RATE * age)
        access_count = entry.get("access_count", 0)
        access_boost = math.log1p(access_count) * 0.2
        tags = entry.get("tags", [])
        tag_boost = len(tags) * 0.05
        return recency + access_boost + tag_boost

    def recall_with_priority(self, category: str = None, limit: int = 10, min_relevance: float = DEFAULT_MIN_RELEVANCE) -> List[Dict]:
        cache_key = f"priority:{category}:{limit}:{min_relevance}"
        cached = self._priority_cache.get(cache_key)
        if cached is not None:
            return cached

        now = time.time()
        all_entries: List[Dict] = []
        layers = [self.layers[category]] if category and category in self.layers else self.layers.values()
        for layer in layers:
            entries = layer.read_jsonl(500)
            for entry in entries:
                entry["_layer"] = layer.name
                entry["_priority"] = self._score_by_priority(entry, now)
                all_entries.append(entry)

        all_entries.sort(key=lambda x: x.get("_priority", 0), reverse=True)
        filtered = [e for e in all_entries if e.get("_priority", 0) >= min_relevance]
        result = filtered[:limit]
        for entry in result:
            entry.pop("_layer", None)
            entry.pop("_priority", None)
        self._priority_cache.put(cache_key, result)
        return result

    def get_relevant_context(self, query: str, category: str = None, max_tokens: int = None) -> str:
        max_tokens = max_tokens or self.max_context_tokens
        relevant = self.recall(query, category, limit=20)
        relevant.extend(self.recall_with_priority(category, limit=20, min_relevance=0.1))

        seen = set()
        unique_relevant = []
        for entry in relevant:
            content = entry.get("content", "")
            if content and content not in seen:
                seen.add(content)
                unique_relevant.append(entry)

        context_parts = []
        current_tokens = 0
        for entry in unique_relevant:
            content = entry.get("content", "")
            entry_tokens = count_tokens(content)
            if current_tokens + entry_tokens <= max_tokens:
                context_parts.append(content)
                current_tokens += entry_tokens
            else:
                remaining = max_tokens - current_tokens
                if remaining > 50:
                    truncated = content[:remaining * 4]
                    if truncated != content:
                        context_parts.append(truncated + "...")
                        break
                break

        return "\n\n---\n\n".join(context_parts)

    def consolidate(self, category: str = None, keep_recent: int = 100):
        layers = [self.layers[category]] if category else list(self.layers.values())
        for layer in layers:
            entries = layer.read_jsonl(10000)
            if len(entries) <= keep_recent:
                continue
            entries.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
            kept = entries[:keep_recent]
            temp_path = layer.jsonl_path.with_suffix(".tmp")
            with open(temp_path, "w") as f:
                for entry in kept:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            layer.jsonl_path.unlink()
            temp_path.rename(layer.jsonl_path)
            layer._index_built = False
            layer._search_cache.clear()
            logger.info(f"Consolidated {layer.name}: kept {keep_recent} entries")

    def get_stats(self) -> Dict:
        stats = {}
        total_entries = 0
        for name, layer in self.layers.items():
            entries = len(layer.read_jsonl(10000))
            stats[name] = entries
            total_entries += entries
        return {"total_entries": total_entries, "layers": stats, "base_dir": str(self.base_dir)}

    def build_system_prompt(self, account_id: str = None, custom_prompt: str = None, platform: str = None, include_context: bool = True) -> str:
        soul = self.load_soul(account_id=account_id)
        identity = self.get_identity()
        parts = []
        if custom_prompt:
            parts.append(custom_prompt)
        elif soul:
            parts.append(soul)
        if platform:
            parts.append(f"\n当前平台: {platform}")
            if platform in ("taobao", "jd", "pdd", "douyin", "kuaishou", "youzan"):
                parts.append("你正在处理电商平台客服对话，回复要专业、简洁、有礼貌。")
            elif platform in ("wecom", "feishu", "dingtalk"):
                parts.append("你正在处理企业办公场景对话，回复要专业高效。")
            else:
                parts.append("你正在处理即时通讯对话，回复要自然亲切。")
        if not parts:
            parts.append(identity or "你是 WanClaw，一个有帮助的 AI 助手。回复使用中文。")
        if include_context:
            context = self.get_relevant_context("", platform or "")
            if context:
                parts.append(f"\n\n相关记忆:\n{context}")
        return "\n".join(parts)


_memory_system: Optional[MemorySystem] = None


def get_memory_system(**kwargs) -> MemorySystem:
    global _memory_system
    if _memory_system is None:
        _memory_system = MemorySystem(**kwargs)
    return _memory_system
