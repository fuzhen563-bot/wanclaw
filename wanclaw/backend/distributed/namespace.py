"""
WanClaw 分布式平台核心模块
租户命名空间隔离 - 确保多租户数据完全隔离
"""

import re
from typing import Optional, Any, Dict, List


class TenantNamespace:
    """
    租户命名空间隔离器
    为每个租户在 Redis 中创建独立的 key 前缀空间
    """

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._validate_tenant_id()

    def _validate_tenant_id(self):
        if not self.tenant_id or not isinstance(self.tenant_id, str):
            raise ValueError("tenant_id must be a non-empty string")
        if not re.match(r'^[a-zA-Z0-9_-]+$', self.tenant_id):
            raise ValueError("tenant_id contains invalid characters")

    def key(self, *parts: str) -> str:
        parts_str = ":".join(str(p) for p in parts)
        return f"wanclaw:tenant:{self.tenant_id}:{parts_str}"

    def session_key(self, session_id: str) -> str:
        return self.key("session", session_id)

    def task_key(self, task_id: str) -> str:
        return self.key("task", task_id)

    def message_key(self, platform: str, chat_id: str) -> str:
        return self.key("message", platform, chat_id)

    def context_key(self, platform: str, chat_id: str, user_id: str) -> str:
        return self.key("context", platform, chat_id, user_id)

    def lock_key(self, resource: str) -> str:
        return self.key("lock", resource)

    def cache_key(self, category: str, key: str) -> str:
        return self.key("cache", category, key)

    def state_key(self, component: str) -> str:
        return self.key("state", component)

    def stats_key(self, metric: str) -> str:
        return self.key("stats", metric)

    def kv_key(self, key: str) -> str:
        return self.key("kv", key)

    def queue_key(self, queue_name: str) -> str:
        return self.key("queue", queue_name)

    def pubsub_channel(self, channel: str) -> str:
        return f"wanclaw:tenant:{self.tenant_id}:pubsub:{channel}"

    @classmethod
    def global_key(cls, *parts: str) -> str:
        parts_str = ":".join(str(p) for p in parts)
        return f"wanclaw:global:{parts_str}"

    @classmethod
    def system_key(cls, *parts: str) -> str:
        parts_str = ":".join(str(p) for p in parts)
        return f"wanclaw:system:{parts_str}"

    @classmethod
    def cluster_key(cls, *parts: str) -> str:
        parts_str = ":".join(str(p) for p in parts)
        return f"wanclaw:cluster:{parts_str}"

    @classmethod
    def node_key(cls, node_id: str, *parts: str) -> str:
        parts_str = ":".join(str(p) for p in parts)
        return f"wanclaw:node:{node_id}:{parts_str}"


class MultiTenantRedis:
    """
    多租户 Redis 客户端
    自动为每个租户注入命名空间隔离
    """

    def __init__(self, redis_client):
        self._redis = redis_client

    def for_tenant(self, tenant_id: str) -> TenantNamespace:
        return TenantNamespace(tenant_id)

    async def set(
        self,
        tenant_id: str,
        key: str,
        value: Any,
        ex: int = None,
        px: int = None,
        nx: bool = False,
        xx: bool = False,
    ):
        ns = TenantNamespace(tenant_id)
        full_key = ns.kv_key(key)
        import json
        if not isinstance(value, str):
            value = json.dumps(value, default=str)
        return await self._redis.set(full_key, value, ex=ex, px=px, nx=nx, xx=xx)

    async def get(self, tenant_id: str, key: str) -> Optional[str]:
        ns = TenantNamespace(tenant_id)
        full_key = ns.kv_key(key)
        return await self._redis.get(full_key)

    async def hset(self, tenant_id: str, key: str, field: str, value: Any) -> int:
        ns = TenantNamespace(tenant_id)
        full_key = ns.kv_key(key)
        import json
        if not isinstance(value, str):
            value = json.dumps(value, default=str)
        return await self._redis.hset(full_key, field, value)

    async def hmset(self, tenant_id: str, key: str, mapping: Dict[str, Any]):
        ns = TenantNamespace(tenant_id)
        full_key = ns.kv_key(key)
        import json
        serialized = {k: json.dumps(v, default=str) if not isinstance(v, str) else v for k, v in mapping.items()}
        return await self._redis.hset(full_key, mapping=serialized)

    async def hget(self, tenant_id: str, key: str, field: str) -> Optional[str]:
        ns = TenantNamespace(tenant_id)
        full_key = ns.kv_key(key)
        return await self._redis.hget(full_key, field)

    async def hgetall(self, tenant_id: str, key: str) -> Dict[str, str]:
        ns = TenantNamespace(tenant_id)
        full_key = ns.kv_key(key)
        import json
        result = await self._redis.hgetall(full_key)
        decoded = {}
        for k, v in result.items():
            try:
                decoded[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                decoded[k] = v
        return decoded

    async def delete(self, tenant_id: str, key: str) -> int:
        ns = TenantNamespace(tenant_id)
        full_key = ns.kv_key(key)
        return await self._redis.delete(full_key)

    async def exists(self, tenant_id: str, key: str) -> int:
        ns = TenantNamespace(tenant_id)
        full_key = ns.kv_key(key)
        return await self._redis.exists(full_key)

    async def expire(self, tenant_id: str, key: str, seconds: int) -> bool:
        ns = TenantNamespace(tenant_id)
        full_key = ns.kv_key(key)
        return await self._redis.expire(full_key, seconds)

    async def zadd(self, tenant_id: str, key: str, mapping: Dict[str, float]) -> int:
        ns = TenantNamespace(tenant_id)
        full_key = ns.kv_key(key)
        return await self._redis.zadd(full_key, mapping)

    async def zrangebyscore(self, tenant_id: str, key: str, min: float, max: float, withscores: bool = False) -> List:
        ns = TenantNamespace(tenant_id)
        full_key = ns.kv_key(key)
        return await self._redis.zrangebyscore(full_key, min, max, withscores=withscores)

    async def zremrangebyscore(self, tenant_id: str, key: str, min: float, max: float) -> int:
        ns = TenantNamespace(tenant_id)
        full_key = ns.kv_key(key)
        return await self._redis.zremrangebyscore(full_key, min, max)

    async def incr(self, tenant_id: str, key: str) -> int:
        ns = TenantNamespace(tenant_id)
        full_key = ns.kv_key(key)
        return await self._redis.incr(full_key)

    async def incrby(self, tenant_id: str, key: str, amount: int) -> int:
        ns = TenantNamespace(tenant_id)
        full_key = ns.kv_key(key)
        return await self._redis.incrby(full_key, amount)

    async def incrbyfloat(self, tenant_id: str, key: str, amount: float) -> float:
        ns = TenantNamespace(tenant_id)
        full_key = ns.kv_key(key)
        return await self._redis.incrbyfloat(full_key, amount)

    async def lpush(self, tenant_id: str, key: str, *values) -> int:
        ns = TenantNamespace(tenant_id)
        full_key = ns.kv_key(key)
        import json
        serialized = [json.dumps(v, default=str) if not isinstance(v, str) else v for v in values]
        return await self._redis.lpush(full_key, *serialized)

    async def lrange(self, tenant_id: str, key: str, start: int, stop: int) -> List[str]:
        ns = TenantNamespace(tenant_id)
        full_key = ns.kv_key(key)
        import json
        result = await self._redis.lrange(full_key, start, stop)
        decoded = []
        for v in result:
            try:
                decoded.append(json.loads(v))
            except (json.JSONDecodeError, TypeError):
                decoded.append(v)
        return decoded

    async def llen(self, tenant_id: str, key: str) -> int:
        ns = TenantNamespace(tenant_id)
        full_key = ns.kv_key(key)
        return await self._redis.llen(full_key)

    async def publish(self, tenant_id: str, channel: str, message: Any) -> int:
        ns = TenantNamespace(tenant_id)
        channel_name = ns.pubsub_channel(channel)
        import json
        if not isinstance(message, str):
            message = json.dumps(message, default=str)
        return await self._redis.publish(channel_name, message)

    def pubsub(self, tenant_id: str = None):
        if tenant_id:
            ns = TenantNamespace(tenant_id)
            pubsub = self._redis.pubsub()
            return pubsub, ns
        return self._redis.pubsub()

    async def scan_iter(self, tenant_id: str, match: str = None) -> List[str]:
        ns = TenantNamespace(tenant_id)
        pattern = ns.key(match or "*")
        keys = []
        async for key in self._redis.scan_iter(match=pattern):
            keys.append(key)
        return keys
