"""
WanClaw 分布式平台核心模块
统一控制平面 - 整合所有分布式组件
管理节点生命周期、路由调度、全局协调
"""

import asyncio
import json
import logging
import uuid
import platform
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime

from .namespace import TenantNamespace
from .state import CentralStateManager, RedisConfig, RedisMode, get_central_state
from .session import UnifiedSessionContext, get_unified_session, SessionType, SessionStatus
from .coordinator import CrossNodeTaskCoordinator, get_task_coordinator, TaskStatus, TaskPriority
from .router import ModelFailoverRouter, get_failover_router, ModelProvider

logger = logging.getLogger(__name__)


@dataclass
class NodeInfo:
    node_id: str
    host: str
    status: str
    capabilities: List[str]
    load: float
    tasks_running: int
    last_heartbeat: datetime
    version: str = "2.0.0"


class PlatformOrchestrator:
    """
    统一控制平面
    整合 Gateway集群 + Redis消息队列 + 会话管理 + 任务调度
    """

    def __init__(self):
        self._node_id = f"node-{uuid.uuid4().hex[:8]}"
        self._state: Optional[CentralStateManager] = None
        self._session: Optional[UnifiedSessionContext] = None
        self._coordinator: Optional[CrossNodeTaskCoordinator] = None
        self._router: Optional[ModelFailoverRouter] = None
        self._running = False
        self._initialized = False

    @property
    def node_id(self) -> str:
        return self._node_id

    async def initialize(self, redis_config: RedisConfig = None):
        if self._initialized:
            return
        self._state = await get_central_state(redis_config)
        self._session = await get_unified_session()
        self._coordinator = await get_task_coordinator()
        self._router = await get_failover_router()
        await self._register_node()
        asyncio.create_task(self._sync_loop())
        self._running = True
        self._initialized = True
        logger.info(f"PlatformOrchestrator initialized: {self._node_id}")

    async def _register_node(self):
        key = TenantNamespace.cluster_key("nodes", self._node_id)
        node_data = {
            "node_id": self._node_id,
            "host": platform.node(),
            "status": "online",
            "capabilities": json.dumps(["ai", "rpa", "workflow", "im"]),
            "load": "0.0",
            "tasks_running": "0",
            "heartbeat": datetime.now().isoformat(),
            "version": "2.0.0",
        }
        await self._state._redis.hset(key, mapping=node_data)
        await self._state._redis.expire(key, 60)

    async def _sync_loop(self):
        while self._running:
            try:
                await asyncio.sleep(30)
                await self._sync_nodes()
            except Exception as e:
                logger.error(f"Sync loop error: {e}")

    async def _sync_nodes(self):
        nodes = await self.list_online_nodes()
        for node in nodes:
            if node.node_id != self._node_id:
                pass

    async def shutdown(self):
        self._running = False
        key = TenantNamespace.cluster_key("nodes", self._node_id)
        if self._state and self._state._redis:
            await self._state._redis.delete(key)
        logger.info(f"PlatformOrchestrator shutdown: {self._node_id}")

    async def create_tenant_session(
        self,
        tenant_id: str,
        platform: str,
        chat_id: str,
        user_id: str,
        session_type: SessionType = SessionType.MIXED,
    ) -> str:
        session_id = f"sess-{uuid.uuid4().hex[:12]}"
        await self._session.create_session(
            session_id=session_id,
            tenant_id=tenant_id,
            session_type=session_type,
            platform=platform,
            chat_id=chat_id,
            user_id=user_id,
            node_id=self._node_id,
        )
        return session_id

    async def send_message_to_session(
        self,
        session_id: str,
        tenant_id: str,
        role: str,
        content: str,
        metadata: Dict[str, Any] = None,
    ) -> bool:
        session = await self._session.add_message(
            session_id=session_id,
            tenant_id=tenant_id,
            role=role,
            content=content,
            metadata=metadata,
        )
        return session is not None

    async def route_ai_request(
        self,
        tenant_id: str,
        prompt: str,
        model_preference: List[str] = None,
    ) -> Dict[str, Any]:
        result = await self._router.route(tenant_id, prompt, model_preference)
        return {
            "success": result.success,
            "provider": result.provider.value,
            "model": result.model_name,
            "response": result.response,
            "error": result.error,
            "latency_ms": result.latency_ms,
            "fallback_used": result.fallback_used,
        }

    async def submit_task(
        self,
        tenant_id: str,
        task_type: str,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> str:
        return await self._coordinator.submit_task(
            tenant_id=tenant_id,
            task_type=task_type,
            payload=payload,
            priority=priority,
        )

    async def claim_next_task(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        task = await self._coordinator.claim_task(tenant_id)
        if not task:
            return None
        return {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "payload": task.payload,
            "checkpoint": task.checkpoint,
        }

    async def update_task_progress(
        self,
        task_id: str,
        tenant_id: str,
        progress: float,
        checkpoint: Dict[str, Any] = None,
    ) -> bool:
        return await self._coordinator.update_progress(task_id, tenant_id, progress, checkpoint)

    async def complete_task(
        self,
        task_id: str,
        tenant_id: str,
        result: Any = None,
    ) -> bool:
        return await self._coordinator.complete_task(task_id, tenant_id, result)

    async def fail_task(
        self,
        task_id: str,
        tenant_id: str,
        error: str,
    ) -> bool:
        return await self._coordinator.fail_task(task_id, tenant_id, error)

    async def migrate_session(
        self,
        session_id: str,
        tenant_id: str,
        target_node_id: str,
    ) -> bool:
        return await self._session.migrate_session(session_id, tenant_id, target_node_id)

    async def migrate_task(
        self,
        task_id: str,
        tenant_id: str,
        target_node_id: str,
    ) -> bool:
        return await self._coordinator.migrate_task(task_id, tenant_id, target_node_id)

    async def get_cluster_status(self) -> Dict[str, Any]:
        nodes = await self.list_online_nodes()
        total_tasks = 0
        total_sessions = 0
        for node in nodes:
            total_tasks += node.tasks_running
        health = await self._state.health_check() if self._state else {"status": "disconnected"}
        return {
            "cluster_name": "wanclaw",
            "total_nodes": len(nodes),
            "online_nodes": sum(1 for n in nodes if n.status == "online"),
            "total_running_tasks": total_tasks,
            "coordinator_healthy": health.get("status") == "healthy",
            "nodes": [
                {
                    "node_id": n.node_id,
                    "host": n.host,
                    "status": n.status,
                    "capabilities": n.capabilities,
                    "load": n.load,
                    "tasks_running": n.tasks_running,
                }
                for n in nodes
            ],
        }

    async def list_online_nodes(self) -> List[NodeInfo]:
        nodes = []
        pattern = TenantNamespace.cluster_key("nodes:*")
        async for key in self._state._redis.scan_iter(match=pattern):
            data = await self._state._redis.hgetall(key)
            if data:
                hb = data.get("heartbeat", "")
                if isinstance(hb, str) and hb:
                    try:
                        hb = datetime.fromisoformat(hb)
                    except (ValueError, TypeError):
                        hb = datetime.now()
                else:
                    hb = datetime.now()
                capabilities = data.get("capabilities", "[]")
                if isinstance(capabilities, str):
                    try:
                        capabilities = json.loads(capabilities)
                    except (json.JSONDecodeError, TypeError):
                        capabilities = []
                nodes.append(
                    NodeInfo(
                        node_id=data.get("node_id", ""),
                        host=data.get("host", ""),
                        status=data.get("status", "unknown"),
                        capabilities=capabilities,
                        load=float(data.get("load", 0.0)),
                        tasks_running=int(data.get("tasks_running", 0)),
                        last_heartbeat=hb,
                    )
                )
        return nodes

    async def get_tenant_stats(self, tenant_id: str) -> Dict[str, Any]:
        active_sessions = await self._session.list_sessions(tenant_id, status=SessionStatus.ACTIVE)
        pending_tasks = await self._coordinator.list_tasks(tenant_id, status=TaskStatus.PENDING)
        running_tasks = await self._coordinator.list_tasks(tenant_id, status=TaskStatus.RUNNING)
        model_status = await self._router.get_model_status(tenant_id) if self._router else []
        return {
            "tenant_id": tenant_id,
            "active_sessions": len(active_sessions),
            "pending_tasks": len(pending_tasks),
            "running_tasks": len(running_tasks),
            "models": model_status,
        }


_orchestrator: Optional[PlatformOrchestrator] = None


async def get_orchestrator(redis_config: RedisConfig = None) -> PlatformOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = PlatformOrchestrator()
        await _orchestrator.initialize(redis_config)
    return _orchestrator


async def shutdown_orchestrator():
    global _orchestrator
    if _orchestrator:
        await _orchestrator.shutdown()
        _orchestrator = None
