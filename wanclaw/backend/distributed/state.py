"""
WanClaw 分布式平台核心模块
中央状态管理器 - Redis Cluster/单节点统一客户端
支持连接池、自动重连、读写分离、哨兵模式
"""

import asyncio
import json
import logging
from typing import Optional, Any, Dict, List, Callable, Set
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import redis.asyncio as aioredis

from .namespace import TenantNamespace, MultiTenantRedis

logger = logging.getLogger(__name__)


class RedisMode(Enum):
    SINGLE = "single"
    SENTINEL = "sentinel"
    CLUSTER = "cluster"


@dataclass
class RedisConfig:
    mode: RedisMode = RedisMode.SINGLE
    url: str = "redis://localhost:6379"
    urls: List[str] = field(default_factory=list)
    password: Optional[str] = None
    db: int = 0
    max_connections: int = 50
    socket_timeout: int = 10
    socket_connect_timeout: int = 5
    retry_on_timeout: bool = True
    retry_on_error: List[int] = field(default_factory=lambda: [1, 2, 3])
    sentinel_master: str = "mymaster"
    cluster_startup_nodes: List[Dict] = field(default_factory=list)
    enable_read_replica: bool = False
    read_replica_url: Optional[str] = None


@dataclass
class StateEntry:
    key: str
    value: Any
    tenant_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    ttl: Optional[int] = None
    version: int = 1


class CentralStateManager:
    """
    中央状态管理器
    统一管理所有节点的状态，同步跨节点数据
    """

    def __init__(self, config: RedisConfig = None):
        self.config = config or RedisConfig()
        self._redis: Optional[aioredis.Redis] = None
        self._read_redis: Optional[aioredis.Redis] = None
        self._pubsub: Optional[aioredis.client.PubSub] = None
        self._subscriptions: Dict[str, Callable] = {}
        self._tenant_redis: Optional[MultiTenantRedis] = None
        self._running = False
        self._lock = asyncio.Lock()

    async def connect(self):
        if self._redis:
            return
        async with self._lock:
            if self._redis:
                return
            if self.config.mode == RedisMode.SINGLE:
                self._redis = aioredis.from_url(
                    self.config.url,
                    password=self.config.password,
                    db=self.config.db,
                    max_connections=self.config.max_connections,
                    socket_timeout=self.config.socket_timeout,
                    socket_connect_timeout=self.config.socket_connect_timeout,
                    retry_on_timeout=self.config.retry_on_timeout,
                    decode_responses=True,
                )
            elif self.config.mode == RedisMode.SENTINEL:
                self._redis = aioredis.Sentinel(
                    self.config.urls,
                    sentinel_kwargs={"password": self.config.password},
                    socket_timeout=self.config.socket_timeout,
                ).master_for(self.config.sentinel_master, redis_class=aioredis.Redis, decode_responses=True)
            elif self.config.mode == RedisMode.CLUSTER:
                self._redis = aioredis.RedisCluster(
                    startup_nodes=self.config.cluster_startup_nodes,
                    password=self.config.password,
                    max_connections=self.config.max_connections,
                    socket_timeout=self.config.socket_timeout,
                    decode_responses=True,
                )
            self._tenant_redis = MultiTenantRedis(self._redis)
            if self.config.enable_read_replica and self.config.read_replica_url:
                self._read_redis = aioredis.from_url(
                    self.config.read_replica_url,
                    password=self.config.password,
                    db=self.config.db,
                    max_connections=self.config.max_connections,
                    decode_responses=True,
                )
            else:
                self._read_redis = self._redis
            self._running = True
            logger.info(f"CentralStateManager connected in {self.config.mode.value} mode")

    async def close(self):
        self._running = False
        if self._redis:
            await self._redis.close()
            self._redis = None
        if self._read_redis and self._read_redis != self._redis:
            await self._read_redis.close()
            self._read_redis = None
        if self._pubsub:
            await self._pubsub.close()
            self._pubsub = None
        self._tenant_redis = None
        logger.info("CentralStateManager closed")

    def for_tenant(self, tenant_id: str) -> TenantNamespace:
        if not self._tenant_redis:
            raise RuntimeError("CentralStateManager not connected")
        return TenantNamespace(tenant_id)

    def tenant_client(self) -> MultiTenantRedis:
        if not self._tenant_redis:
            raise RuntimeError("CentralStateManager not connected")
        return self._tenant_redis

    async def set_with_version(
        self,
        key: str,
        value: Any,
        tenant_id: Optional[str] = None,
        ttl: int = None,
    ) -> int:
        if tenant_id:
            ns = TenantNamespace(tenant_id)
            full_key = ns.kv_key(key)
        else:
            full_key = TenantNamespace.global_key("kv", key)
        version_key = f"{full_key}:_v"
        version = await self._redis.incr(version_key)
        import time
        data = {
            "value": value if isinstance(value, str) else json.dumps(value, default=str),
            "version": version,
            "updated_at": datetime.now().isoformat(),
        }
        await self._redis.set(full_key, json.dumps(data, default=str), ex=ttl)
        await self._redis.set(version_key, version, ex=ttl)
        return version

    async def get_with_version(self, key: str, tenant_id: Optional[str] = None) -> tuple[Optional[Any], int]:
        if tenant_id:
            ns = TenantNamespace(tenant_id)
            full_key = ns.kv_key(key)
        else:
            full_key = TenantNamespace.global_key("kv", key)
        data = await self._redis.get(full_key)
        if not data:
            return None, 0
        try:
            parsed = json.loads(data)
            return parsed.get("value"), parsed.get("version", 0)
        except (json.JSONDecodeError, TypeError):
            return data, 0

    async def compare_and_set(
        self,
        key: str,
        expected_version: int,
        new_value: Any,
        tenant_id: Optional[str] = None,
        ttl: int = None,
    ) -> bool:
        if tenant_id:
            ns = TenantNamespace(tenant_id)
            full_key = ns.kv_key(key)
        else:
            full_key = TenantNamespace.global_key("kv", key)
        version_key = f"{full_key}:_v"
        current_version = await self._redis.get(version_key)
        if current_version is None:
            current_version = 0
        else:
            current_version = int(current_version)
        if current_version != expected_version:
            return False
        version = await self.set_with_version(key, new_value, tenant_id, ttl)
        return version == expected_version + 1

    async def watch_keys(self, *keys: str) -> Callable:
        async def _release():
            pass
        return _release

    @asynccontextmanager
    async def pipeline(self):
        pipe = self._redis.pipeline(transaction=True)
        try:
            yield pipe
        finally:
            await pipe.execute()

    async def subscribe(self, channel: str, handler: Callable, tenant_id: Optional[str] = None):
        if not self._pubsub:
            self._pubsub = self._redis.pubsub()
        if tenant_id:
            ns = TenantNamespace(tenant_id)
            channel_name = ns.pubsub_channel(channel)
        else:
            channel_name = TenantNamespace.cluster_key("pubsub", channel)
        await self._pubsub.subscribe(channel_name)
        self._subscriptions[channel_name] = handler
        logger.info(f"Subscribed to channel: {channel_name}")

    async def unsubscribe(self, channel: str, tenant_id: Optional[str] = None):
        if not self._pubsub:
            return
        if tenant_id:
            ns = TenantNamespace(tenant_id)
            channel_name = ns.pubsub_channel(channel)
        else:
            channel_name = TenantNamespace.cluster_key("pubsub", channel)
        await self._pubsub.unsubscribe(channel_name)
        self._subscriptions.pop(channel_name, None)

    async def publish(self, channel: str, message: Any, tenant_id: Optional[str] = None) -> int:
        if tenant_id:
            ns = TenantNamespace(tenant_id)
            channel_name = ns.pubsub_channel(channel)
        else:
            channel_name = TenantNamespace.cluster_key("pubsub", channel)
        msg = message if isinstance(message, str) else json.dumps(message, default=str)
        return await self._redis.publish(channel_name, msg)

    async def start_listening(self):
        if not self._pubsub:
            return
        async def _listen():
            while self._running:
                try:
                    msg = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if msg and msg["type"] == "message":
                        channel = msg["channel"]
                        handler = self._subscriptions.get(channel)
                        if handler:
                            try:
                                data = msg["data"]
                                try:
                                    data = json.loads(data)
                                except (json.JSONDecodeError, TypeError):
                                    pass
                                asyncio.create_task(handler(data))
                            except Exception as e:
                                logger.error(f"Handler error for {channel}: {e}")
                except Exception as e:
                    logger.error(f"Listen error: {e}")
                    await asyncio.sleep(1)
        asyncio.create_task(_listen())

    async def acquire_lock(
        self,
        resource: str,
        tenant_id: Optional[str] = None,
        timeout: int = 10,
        lock_timeout: int = 30,
    ) -> Optional[str]:
        if tenant_id:
            ns = TenantNamespace(tenant_id)
            lock_key = ns.lock_key(resource)
        else:
            lock_key = TenantNamespace.global_key("lock", resource)
        lock_id = f"{asyncio.current_task().get_name()}-{datetime.now().timestamp()}"
        import time
        end_time = time.time() + timeout
        while time.time() < end_time:
            acquired = await self._redis.set(lock_key, lock_id, nx=True, ex=lock_timeout)
            if acquired:
                return lock_id
            await asyncio.sleep(0.1)
        return None

    async def release_lock(self, resource: str, lock_id: str, tenant_id: Optional[str] = None) -> bool:
        if tenant_id:
            ns = TenantNamespace(tenant_id)
            lock_key = ns.lock_key(resource)
        else:
            lock_key = TenantNamespace.global_key("lock", resource)
        current = await self._redis.get(lock_key)
        if current == lock_id:
            await self._redis.delete(lock_key)
            return True
        return False

    async def get_all_tenant_keys(self, tenant_id: str, pattern: str = "*") -> List[str]:
        ns = TenantNamespace(tenant_id)
        full_pattern = ns.key(pattern)
        keys = []
        async for key in self._redis.scan_iter(match=full_pattern):
            keys.append(key)
        return keys

    async def health_check(self) -> Dict[str, Any]:
        if not self._redis:
            return {"status": "disconnected"}
        try:
            start = asyncio.get_event_loop().time()
            await self._redis.ping()
            latency = (asyncio.get_event_loop().time() - start) * 1000
            info = await self._redis.info("memory")
            return {
                "status": "healthy",
                "mode": self.config.mode.value,
                "latency_ms": round(latency, 2),
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


_central_state: Optional[CentralStateManager] = None


async def get_central_state(config: RedisConfig = None) -> CentralStateManager:
    global _central_state
    if _central_state is None:
        _central_state = CentralStateManager(config)
        await _central_state.connect()
    return _central_state


async def close_central_state():
    global _central_state
    if _central_state:
        await _central_state.close()
        _central_state = None
