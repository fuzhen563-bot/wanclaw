"""
分布式Gateway模块
支持多节点集群、消息广播、会话同步
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class MessagePriority(Enum):
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


@dataclass
class GatewayNode:
    node_id: str
    host: str
    port: int
    status: str = "online"
    capabilities: List[str] = field(default_factory=list)
    load: float = 0.0
    last_heartbeat: datetime = field(default_factory=datetime.now)


@dataclass
class SessionState:
    session_id: str
    user_id: str
    platform: str
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    ttl: int = 3600


class DistributedGateway:
    """分布式Gateway核心"""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        node_id: str = None,
        cluster_name: str = "wanclaw",
    ):
        self.redis_url = redis_url
        self.node_id = node_id or f"node-{uuid.uuid4().hex[:8]}"
        self.cluster_name = cluster_name
        self.redis: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None
        self.subscriptions: Dict[str, Callable] = {}
        self.nodes: Dict[str, GatewayNode] = {}
        self._running = False

    async def connect(self):
        """连接Redis"""
        self.redis = await aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        self.pubsub = self.redis.pubsub()
        await self._register_node()
        logger.info(f"Distributed Gateway connected: {self.node_id}")

    async def close(self):
        """关闭连接"""
        self._running = False
        if self.pubsub:
            await self.pubsub.close()
        if self.redis:
            await self.redis.close()
        await self._unregister_node()

    async def _register_node(self):
        """注册当前节点"""
        key = f"{self.cluster_name}:nodes:{self.node_id}"
        node_data = {
            "node_id": self.node_id,
            "host": "localhost",
            "port": 8000,
            "status": "online",
            "capabilities": "ai,skills,rpa",
            "load": "0.0",
            "heartbeat": datetime.now().isoformat(),
        }
        await self.redis.hset(key, mapping=node_data)
        await self.redis.expire(key, 30)
        
        # 启动心跳
        asyncio.create_task(self._heartbeat_loop())

    async def _unregister_node(self):
        """注销节点"""
        key = f"{self.cluster_name}:nodes:{self.node_id}"
        await self.redis.delete(key)

    async def _heartbeat_loop(self):
        """心跳维持"""
        while self._running:
            try:
                key = f"{self.cluster_name}:nodes:{self.node_id}"
                await self.redis.hset(key, "heartbeat", datetime.now().isoformat())
                await self.redis.expire(key, 30)
                
                # 清理离线节点
                await self._cleanup_offline_nodes()
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
            
            await asyncio.sleep(10)

    async def _cleanup_offline_nodes(self):
        """清理离线节点"""
        pattern = f"{self.cluster_name}:nodes:*"
        async for key in self.redis.scan_iter(match=pattern):
            node_data = await self.redis.hgetall(key)
            if node_data:
                heartbeat = node_data.get("heartbeat")
                if heartbeat:
                    last_time = datetime.fromisoformat(heartbeat)
                    if datetime.now() - last_time > timedelta(seconds=30):
                        await self.redis.delete(key)

    async def get_nodes(self) -> Dict[str, GatewayNode]:
        """获取所有在线节点"""
        nodes = {}
        pattern = f"{self.cluster_name}:nodes:*"
        async for key in self.redis.scan_iter(match=pattern):
            node_data = await self.redis.hgetall(key)
            if node_data and node_data.get("status") == "online":
                node_id = node_data["node_id"]
                nodes[node_id] = GatewayNode(
                    node_id=node_id,
                    host=node_data.get("host", "localhost"),
                    port=int(node_data.get("port", 8000)),
                    status=node_data.get("status", "online"),
                    capabilities=node_data.get("capabilities", "").split(","),
                    load=float(node_data.get("load", 0.0)),
                )
        self.nodes = nodes
        return nodes

    async def broadcast(self, channel: str, message: Dict[str, Any], priority: MessagePriority = MessagePriority.NORMAL):
        """向所有节点广播消息"""
        channel_name = f"{self.cluster_name}:{channel}"
        message["from_node"] = self.node_id
        message["timestamp"] = datetime.now().isoformat()
        message["priority"] = priority.value
        
        await self.redis.publish(channel_name, json.dumps(message))
        logger.debug(f"Broadcast to {channel_name}: {message.get('type')}")

    async def subscribe(self, channel: str, handler: Callable[[Dict], Any]):
        """订阅频道"""
        channel_name = f"{self.cluster_name}:{channel}"
        self.subscriptions[channel_name] = handler
        await self.pubsub.subscribe(channel_name)
        logger.info(f"Subscribed to {channel_name}")

    async def start_listening(self):
        """开始监听消息"""
        self._running = True
        asyncio.create_task(self._listen_loop())

    async def _listen_loop(self):
        """消息监听循环"""
        while self._running:
            try:
                message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message["type"] == "message":
                    channel = message["channel"]
                    data = json.loads(message["data"])
                    
                    if channel in self.subscriptions:
                        handler = self.subscriptions[channel]
                        await handler(data)
            except Exception as e:
                logger.error(f"Listen error: {e}")
                await asyncio.sleep(1)

    async def send_to_node(self, node_id: str, message: Dict[str, Any]):
        """发送消息到指定节点"""
        channel = f"{self.cluster_name}:node:{node_id}"
        message["from_node"] = self.node_id
        message["timestamp"] = datetime.now().isoformat()
        await self.redis.publish(channel, json.dumps(message))

    async def forward_message(self, message: Dict[str, Any], target_node: str = None):
        """转发消息（智能路由）"""
        if target_node:
            await self.send_to_node(target_node, message)
        else:
            # 负载均衡选择节点
            nodes = await self.get_nodes()
            if nodes:
                target = min(nodes.values(), key=lambda n: n.load)
                await self.send_to_node(target.node_id, message)


class SessionStore:
    """分布式会话存储"""

    def __init__(self, redis_client: aioredis.Redis, cluster_name: str = "wanclaw"):
        self.redis = redis_client
        self.cluster_name = cluster_name

    def _session_key(self, session_id: str) -> str:
        return f"{self.cluster_name}:session:{session_id}"

    async def set(self, session: SessionState):
        """保存会话"""
        key = self._session_key(session.session_id)
        data = {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "platform": session.platform,
            "data": json.dumps(session.data),
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        }
        await self.redis.hset(key, mapping=data)
        await self.redis.expire(key, session.ttl)

    async def get(self, session_id: str) -> Optional[SessionState]:
        """获取会话"""
        key = self._session_key(session_id)
        data = await self.redis.hgetall(key)
        if not data:
            return None
        
        return SessionState(
            session_id=data["session_id"],
            user_id=data["user_id"],
            platform=data["platform"],
            data=json.loads(data["data"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )

    async def delete(self, session_id: str):
        """删除会话"""
        key = self._session_key(session_id)
        await self.redis.delete(key)

    async def update_data(self, session_id: str, data: Dict[str, Any]):
        """更新会话数据"""
        key = self._session_key(session_id)
        current = await self.get(session_id)
        if current:
            current.data.update(data)
            current.updated_at = datetime.now()
            await self.set(current)

    async def list_user_sessions(self, user_id: str) -> List[SessionState]:
        """列出用户的所有会话"""
        sessions = []
        pattern = f"{self.cluster_name}:session:*"
        async for key in self.redis.scan_iter(match=pattern):
            data = await self.redis.hgetall(key)
            if data and data.get("user_id") == user_id:
                sessions.append(SessionState(
                    session_id=data["session_id"],
                    user_id=data["user_id"],
                    platform=data["platform"],
                    data=json.loads(data["data"]),
                    created_at=datetime.fromisoformat(data["created_at"]),
                    updated_at=datetime.fromisoformat(data["updated_at"]),
                ))
        return sessions


class MessageQueue:
    """Redis Streams消息队列"""

    def __init__(self, redis_client: aioredis.Redis, queue_name: str = "wanclaw"):
        self.redis = redis_client
        self.queue_name = f"{queue_name}:queue"

    async def enqueue(self, message: Dict[str, Any], priority: int = 0):
        """入队"""
        msg_id = await self.redis.xadd(
            self.queue_name,
            {"data": json.dumps(message), "priority": str(priority)},
        )
        return msg_id

    async def dequeue(self, count: int = 1, block_ms: int = 5000) -> List[Dict]:
        """出队（阻塞）"""
        result = await self.redis.xread({self.queue_name: "0"}, count=count, block=block_ms)
        messages = []
        if result:
            for stream, msgs in result:
                for msg_id, fields in msgs:
                    messages.append({
                        "id": msg_id,
                        "data": json.loads(fields["data"]),
                        "priority": int(fields.get("priority", 0)),
                    })
        return messages

    async def ack(self, message_id: str):
        """确认处理"""
        await self.redis.xdel(self.queue_name, message_id)

    async def get_queue_length(self) -> int:
        """获取队列长度"""
        return await self.redis.xlen(self.queue_name)


_gateway_instance: Optional[DistributedGateway] = None
_session_store: Optional[SessionStore] = None
_message_queue: Optional[MessageQueue] = None


async def get_distributed_gateway(
    redis_url: str = "redis://localhost:6379",
    node_id: str = None,
    cluster_name: str = "wanclaw",
) -> DistributedGateway:
    """获取分布式Gateway单例"""
    global _gateway_instance
    if _gateway_instance is None:
        _gateway_instance = DistributedGateway(redis_url, node_id, cluster_name)
        await _gateway_instance.connect()
    return _gateway_instance


async def get_session_store() -> SessionStore:
    """获取会话存储单例"""
    global _session_store
    if _session_store is None:
        redis = await aioredis.from_url("redis://localhost:6379")
        _session_store = SessionStore(redis)
    return _session_store


async def get_message_queue() -> MessageQueue:
    """获取消息队列单例"""
    global _message_queue
    if _message_queue is None:
        redis = await aioredis.from_url("redis://localhost:6379")
        _message_queue = MessageQueue(redis)
    return _message_queue