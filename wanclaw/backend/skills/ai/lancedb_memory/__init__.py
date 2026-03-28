"""
LanceDB 记忆技能
向量语义搜索 + 多模态记忆存储，支持会话级记忆管理

功能：
- 添加记忆条目（自动向量嵌入）
- 语义搜索记忆
- 会话级记忆管理
- 记忆分类标签
- 相似记忆推荐
- 记忆版本追踪
"""

import os
import time
import uuid
import logging
from typing import Dict, List, Optional, Any, Literal
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from wanclaw.backend.skills import BaseSkill, SkillResult, SkillCategory, SkillLevel

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    CONVERSATION = "conversation"    # 对话记录
    FACT = "fact"                  # 事实知识
    PREFERENCE = "preference"       # 用户偏好
    WORKFLOW = "workflow"           # 工作流记忆
    CONTEXT = "context"            # 上下文片段
    DOCUMENT = "document"           # 文档摘要


@dataclass
class MemoryEntry:
    id: str
    content: str
    session_id: str
    memory_type: str
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5  # 0.0 ~ 1.0
    created_at: str = ""
    updated_at: str = ""
    version: int = 1
    parent_id: Optional[str] = None  # 用于记忆链追踪


class LanceDBMemorySkill(BaseSkill):
    """LanceDB 向量记忆技能"""

    def __init__(self):
        super().__init__()
        self.name = "LanceDBMemory"
        self.description = (
            "向量记忆存储与检索：添加记忆、语义搜索、会话管理、"
            "相似推荐、标签分类、版本追踪"
        )
        self.category = SkillCategory.AI
        self.level = SkillLevel.INTERMEDIATE

        self.required_params = ["action"]
        self.optional_params = {
            "content": str,
            "session_id": str,
            "memory_type": str,
            "tags": list,
            "metadata": dict,
            "importance": float,
            "limit": int,
            "threshold": float,
            "query": str,
            "memory_id": str,
            "ids": list,
            "parent_id": str,
            "days": int,
            "table_name": str,
        }

        self._db = None
        self._table = None
        self._embedding = None
        self._initialized = False
        self._data_dir = "./data/lancedb_memory"

    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        action = params.get("action", "").lower()
        try:
            await self._ensure_initialized()

            method = getattr(self, f"_action_{action}", None)
            if not method:
                return SkillResult(
                    success=False,
                    message=f"不支持的操作: {action}",
                    error=f"Unknown action: {action}"
                )
            return await method(params)
        except Exception as e:
            logger.error(f"LanceDB记忆操作失败 [{action}]: {e}")
            return SkillResult(
                success=False,
                message=f"记忆操作失败: {str(e)}",
                error=str(e)
            )

    async def _ensure_initialized(self):
        if self._initialized:
            return
        try:
            import lancedb
            self._db = lancedb.connect(self._data_dir)
            self._initialized = True
            logger.info(f"LanceDB connected: {self._data_dir}")
        except ImportError:
            raise ImportError(
                "lancedb 未安装，请运行: pip install lancedb"
            )

    def _get_embedding(self, texts: List[str]) -> List[List[float]]:
        if self._embedding is None:
            try:
                import httpx
                ollama_url = os.environ.get(
                    "OLLAMA_BASE_URL", "http://localhost:11434"
                )
                resp = httpx.post(
                    f"{ollama_url}/api/embeddings",
                    json={"model": "nomic-embed-text", "prompt": texts[0]},
                    timeout=30,
                )
                if resp.status_code == 200:
                    return [resp.json().get("embedding", [])]
            except Exception:
                pass
            try:
                from transformers import AutoTokenizer, AutoModel
                import torch
                model_name = os.environ.get(
                    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
                )
                tokenizer = AutoTokenizer.from_pretrained(model_name)
                model = AutoModel.from_pretrained(model_name)
                model.eval()

                def mean_pooling(md, inpt):
                    token_emb = md(**inpt)
                    return token_emb.last_hidden_state.mean(dim=1)

                with torch.no_grad():
                    inputs = tokenizer(
                        texts,
                        padding=True,
                        truncation=True,
                        return_tensors="pt"
                    )
                    embeddings = mean_pooling(model, inputs)
                    embeddings = embeddings / embeddings.norm(dim=1, keepdim=True)
                    return embeddings.numpy().tolist()
            except Exception:
                pass
            import hashlib
            import struct
            embeddings = []
            for text in texts:
                h = hashlib.sha256(text.encode()).digest()
                vec = list(struct.unpack(f"{len(h)//4}f", h[:32]))
                while len(vec) < 384:
                    vec.extend(vec[:min(len(vec), 384 - len(vec))])
                embeddings.append(vec[:384])
            return embeddings

    async def _get_or_create_table(self, table_name: str = "memory"):
        await self._ensure_initialized()
        try:
            return self._db.open_table(table_name)
        except Exception:
            schema = {
                "id": "string",
                "content": "string",
                "session_id": "string",
                "memory_type": "string",
                "tags": "list<string>",
                "metadata": "json",
                "importance": "float",
                "created_at": "string",
                "updated_at": "string",
                "version": "int32",
                "parent_id": "string",
                "vector": "list<float>",
            }
            tbl = self._db.create_table(
                table_name,
                schema=schema,
                exist_ok=True,
            )
            return tbl

    async def _action_add(self, params: Dict) -> SkillResult:
        """添加记忆条目"""
        content = params.get("content", "")
        if not content:
            return SkillResult(
                success=False,
                message="记忆内容不能为空",
                error="content is required"
            )

        table_name = params.get("table_name", "memory")
        table = await self._get_or_create_table(table_name)

        memory_id = str(uuid.uuid4())
        session_id = params.get("session_id", "default")
        memory_type = params.get("memory_type", MemoryType.CONVERSATION.value)
        tags = params.get("tags", [])
        metadata = params.get("metadata", {})
        importance = params.get("importance", 0.5)
        parent_id = params.get("parent_id")

        now = datetime.now().isoformat()

        embeddings = self._get_embedding([content])
        vector = embeddings[0] if embeddings else []

        entry = {
            "id": memory_id,
            "content": content,
            "session_id": session_id,
            "memory_type": memory_type,
            "tags": tags,
            "metadata": metadata,
            "importance": importance,
            "created_at": now,
            "updated_at": now,
            "version": 1,
            "parent_id": parent_id or "",
            "vector": vector,
        }

        table.add([entry])

        logger.info(f"记忆添加成功: {memory_id} [{session_id}]")
        return SkillResult(
            success=True,
            message=f"记忆添加成功",
            data={
                "memory_id": memory_id,
                "session_id": session_id,
                "memory_type": memory_type,
                "created_at": now,
                "importance": importance,
            }
        )

    async def _action_search(self, params: Dict) -> SkillResult:
        """语义搜索记忆"""
        query = params.get("query", "")
        if not query:
            return SkillResult(
                success=False,
                message="搜索关键词不能为空",
                error="query is required"
            )

        table_name = params.get("table_name", "memory")
        table = await self._get_or_create_table(table_name)

        limit = params.get("limit", 5)
        session_id = params.get("session_id")
        memory_type = params.get("memory_type")
        tags = params.get("tags")
        threshold = params.get("threshold", 0.0)

        query_emb = self._get_embedding([query])[0]

        results = table.search(query_emb, vector_column_name="vector").limit(limit * 3)

        if session_id:
            results = results.where(f'session_id = "{session_id}"')
        if memory_type:
            type_filter = f'memory_type = "{memory_type}"'
            try:
                results = results.where(type_filter)
            except Exception:
                pass

        raw_results = results.to_list()

        filtered = []
        for r in raw_results:
            if r.get("score", 0) >= threshold:
                if tags:
                    entry_tags = r.get("tags", [])
                    if not any(t in entry_tags for t in tags):
                        continue
                filtered.append({
                    "id": r["id"],
                    "content": r["content"],
                    "session_id": r.get("session_id", ""),
                    "memory_type": r.get("memory_type", ""),
                    "tags": r.get("tags", []),
                    "importance": r.get("importance", 0.5),
                    "created_at": r.get("created_at", ""),
                    "score": round(r.get("score", 0), 4),
                    "metadata": r.get("metadata", {}),
                })
            if len(filtered) >= limit:
                break

        return SkillResult(
            success=True,
            message=f"找到 {len(filtered)} 条相关记忆",
            data={
                "query": query,
                "results": filtered,
                "total": len(filtered),
            }
        )

    async def _action_get(self, params: Dict) -> SkillResult:
        """获取单条记忆详情"""
        memory_id = params.get("memory_id")
        if not memory_id:
            return SkillResult(
                success=False,
                message="需要记忆 ID",
                error="memory_id is required"
            )

        table_name = params.get("table_name", "memory")
        table = await self._get_or_create_table(table_name)

        results = table.search().where(f'id = "{memory_id}"').limit(1).to_list()

        if not results:
            return SkillResult(
                success=False,
                message=f"记忆不存在: {memory_id}",
                error="memory not found"
            )

        r = results[0]
        return SkillResult(
            success=True,
            message="记忆获取成功",
            data={
                "id": r["id"],
                "content": r["content"],
                "session_id": r.get("session_id", ""),
                "memory_type": r.get("memory_type", ""),
                "tags": r.get("tags", []),
                "metadata": r.get("metadata", {}),
                "importance": r.get("importance", 0.5),
                "created_at": r.get("created_at", ""),
                "updated_at": r.get("updated_at", ""),
                "version": r.get("version", 1),
                "parent_id": r.get("parent_id", ""),
            }
        )

    async def _action_update(self, params: Dict) -> SkillResult:
        """更新记忆内容"""
        memory_id = params.get("memory_id")
        content = params.get("content")
        if not memory_id:
            return SkillResult(
                success=False,
                message="需要记忆 ID",
                error="memory_id is required"
            )

        table_name = params.get("table_name", "memory")
        table = await self._get_or_create_table(table_name)

        results = table.search().where(f'id = "{memory_id}"').limit(1).to_list()

        if not results:
            return SkillResult(
                success=False,
                message=f"记忆不存在: {memory_id}",
                error="memory not found"
            )

        existing = results[0]
        old_parent_id = existing.get("id", "")

        if content is None:
            content = existing["content"]

        now = datetime.now().isoformat()
        embeddings = self._get_embedding([content])[0]
        new_version = existing.get("version", 1) + 1

        update_entry = {
            "id": str(uuid.uuid4()),
            "content": content,
            "session_id": existing.get("session_id", "default"),
            "memory_type": params.get("memory_type", existing.get("memory_type", "conversation")),
            "tags": params.get("tags", existing.get("tags", [])),
            "metadata": params.get("metadata", existing.get("metadata", {})),
            "importance": params.get("importance", existing.get("importance", 0.5)),
            "created_at": now,
            "updated_at": now,
            "version": new_version,
            "parent_id": old_parent_id,
            "vector": embeddings,
        }

        table.add([update_entry])

        logger.info(f"记忆更新成功: {memory_id} -> {update_entry['id']} (v{new_version})")
        return SkillResult(
            success=True,
            message=f"记忆已更新为 v{new_version}",
            data={
                "old_id": memory_id,
                "new_id": update_entry["id"],
                "version": new_version,
                "parent_id": old_parent_id,
            }
        )

    async def _action_delete(self, params: Dict) -> SkillResult:
        """删除记忆"""
        memory_ids = params.get("ids", [])
        if not memory_ids:
            memory_id = params.get("memory_id")
            if memory_id:
                memory_ids = [memory_id]

        if not memory_ids:
            return SkillResult(
                success=False,
                message="需要提供记忆 ID 列表",
                error="ids or memory_id is required"
            )

        table_name = params.get("table_name", "memory")
        table = await self._get_or_create_table(table_name)

        deleted = 0
        for mid in memory_ids:
            try:
                table.delete(f'id = "{mid}"')
                deleted += 1
            except Exception as e:
                logger.warning(f"删除记忆 {mid} 失败: {e}")

        return SkillResult(
            success=True,
            message=f"已删除 {deleted}/{len(memory_ids)} 条记忆",
            data={"deleted": deleted, "total_requested": len(memory_ids)}
        )

    async def _action_list(self, params: Dict) -> SkillResult:
        """列出记忆"""
        table_name = params.get("table_name", "memory")
        table = await self._get_or_create_table(table_name)

        limit = params.get("limit", 20)
        session_id = params.get("session_id")

        try:
            if session_id:
                results = (
                    table.search()
                    .where(f'session_id = "{session_id}"')
                    .limit(limit)
                    .to_list()
                )
            else:
                results = table.search().limit(limit).to_list()
        except Exception:
            results = []

        entries = [{
            "id": r["id"],
            "content": r.get("content", "")[:200],
            "session_id": r.get("session_id", ""),
            "memory_type": r.get("memory_type", ""),
            "tags": r.get("tags", []),
            "importance": r.get("importance", 0.5),
            "created_at": r.get("created_at", ""),
            "version": r.get("version", 1),
        } for r in results]

        return SkillResult(
            success=True,
            message=f"共 {len(entries)} 条记忆",
            data={"entries": entries, "total": len(entries)}
        )

    async def _action_session_history(self, params: Dict) -> SkillResult:
        """获取会话历史记忆链"""
        session_id = params.get("session_id")
        if not session_id:
            return SkillResult(
                success=False,
                message="需要 session_id",
                error="session_id is required"
            )

        table_name = params.get("table_name", "memory")
        table = await self._get_or_create_table(table_name)

        limit = params.get("limit", 50)

        try:
            results = (
                table.search()
                .where(f'session_id = "{session_id}"')
                .limit(limit)
                .to_list()
            )
        except Exception:
            results = []

        chain = []
        for r in results:
            chain.append({
                "id": r["id"],
                "content": r["content"],
                "memory_type": r.get("memory_type", ""),
                "importance": r.get("importance", 0.5),
                "created_at": r.get("created_at", ""),
                "version": r.get("version", 1),
                "parent_id": r.get("parent_id", ""),
            })

        chain.sort(key=lambda x: x.get("created_at", ""))

        return SkillResult(
            success=True,
            message=f"会话 {session_id} 共有 {len(chain)} 条记忆",
            data={"session_id": session_id, "chain": chain}
        )

    async def _action_cleanup(self, params: Dict) -> SkillResult:
        """清理过期记忆"""
        days = params.get("days", 30)
        session_id = params.get("session_id")
        memory_type = params.get("memory_type")
        table_name = params.get("table_name", "memory")
        table = await self._get_or_create_table(table_name)

        cutoff = datetime.now().timestamp() - (days * 86400)
        cutoff_str = datetime.fromtimestamp(cutoff).isoformat()

        conditions = [f'created_at < "{cutoff_str}"']
        if session_id:
            conditions.append(f'session_id = "{session_id}"')
        if memory_type:
            conditions.append(f'memory_type = "{memory_type}"')

        where_clause = " AND ".join(conditions)

        try:
            results = table.search().where(where_clause).limit(1000).to_list()
            deleted = 0
            for r in results:
                try:
                    table.delete(f'id = "{r["id"]}"')
                    deleted += 1
                except Exception:
                    pass
        except Exception:
            deleted = 0

        logger.info(f"清理了 {deleted} 条过期记忆（{days}天前）")
        return SkillResult(
            success=True,
            message=f"已清理 {deleted} 条过期记忆",
            data={"deleted": deleted, "days": days}
        )

    async def _action_stats(self, params: Dict) -> SkillResult:
        """记忆统计"""
        table_name = params.get("table_name", "memory")
        table = await self._get_or_create_table(table_name)

        try:
            all_data = table.search().limit(10000).to_list()
        except Exception:
            all_data = []

        sessions = set()
        types_count: Dict[str, int] = {}
        tags_count: Dict[str, int] = {}

        for r in all_data:
            sessions.add(r.get("session_id", ""))
            t = r.get("memory_type", "unknown")
            types_count[t] = types_count.get(t, 0) + 1
            for tag in r.get("tags", []):
                tags_count[tag] = tags_count.get(tag, 0) + 1

        return SkillResult(
            success=True,
            message="记忆统计完成",
            data={
                "total_memories": len(all_data),
                "total_sessions": len(sessions),
                "by_type": types_count,
                "top_tags": sorted(tags_count.items(), key=lambda x: -x[1])[:10],
                "storage_path": self._data_dir,
            }
        )

    async def _action_similar(self, params: Dict) -> SkillResult:
        """查找相似记忆"""
        memory_id = params.get("memory_id")
        if not memory_id:
            return SkillResult(
                success=False,
                message="需要 memory_id",
                error="memory_id is required"
            )

        table_name = params.get("table_name", "memory")
        table = await self._get_or_create_table(table_name)

        results = table.search().where(f'id = "{memory_id}"').limit(1).to_list()
        if not results:
            return SkillResult(
                success=False,
                message=f"记忆不存在: {memory_id}",
                error="memory not found"
            )

        source = results[0]
        limit = params.get("limit", 5)

        similar = (
            table.search(source["vector"], vector_column_name="vector")
            .limit(limit + 1)
            .to_list()
        )

        results_out = []
        for r in similar:
            if r["id"] != memory_id and r.get("score", 0) > 0.5:
                results_out.append({
                    "id": r["id"],
                    "content": r["content"],
                    "session_id": r.get("session_id", ""),
                    "memory_type": r.get("memory_type", ""),
                    "score": round(r.get("score", 0), 4),
                    "created_at": r.get("created_at", ""),
                })
            if len(results_out) >= limit:
                break

        return SkillResult(
            success=True,
            message=f"找到 {len(results_out)} 条相似记忆",
            data={
                "source_id": memory_id,
                "similar": results_out,
            }
        )
