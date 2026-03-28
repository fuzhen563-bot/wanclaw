"""
WanClaw 分布式平台核心模块
跨节点任务协调器 - 任务分发、断点续传、失败迁移
基于Redis Streams实现分布式任务队列
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .namespace import TenantNamespace
from .state import CentralStateManager, get_central_state

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DLQ = "dlq"


class TaskPriority(Enum):
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


@dataclass
class Task:
    task_id: str
    tenant_id: str
    task_type: str
    payload: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    assigned_node: Optional[str] = None
    progress: float = 0.0
    checkpoint: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    max_retries: int = 3
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    task_id: str
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    checkpoint: Optional[Dict[str, Any]] = None


class CrossNodeTaskCoordinator:
    """
    跨节点任务协调器
    - 任务分发到最优节点
    - 断点续传（checkpoint恢复）
    - 失败重试与DLQ
    - 节点健康感知负载均衡
    """

    def __init__(self, state: CentralStateManager = None):
        self._state = state
        self._node_id = f"node-{uuid.uuid4().hex[:8]}"
        self._local_tasks: Dict[str, Task] = {}
        self._handlers: Dict[str, Callable] = {}
        self._running = False

    async def initialize(self):
        if self._state is None:
            self._state = await get_central_state()
        await self._register_node()
        self._running = True
        asyncio.create_task(self._heartbeat_loop())
        asyncio.create_task(self._retry_loop())

    @property
    def node_id(self) -> str:
        return self._node_id

    async def _register_node(self):
        key = TenantNamespace.cluster_key("nodes", self._node_id)
        import platform
        node_data = {
            "node_id": self._node_id,
            "host": platform.node(),
            "status": "online",
            "capabilities": "ai,rpa,workflow",
            "load": "0.0",
            "heartbeat": datetime.now().isoformat(),
            "tasks_running": 0,
        }
        await self._state._redis.hset(key, mapping=node_data)
        await self._state._redis.expire(key, 60)

    async def _heartbeat_loop(self):
        while self._running:
            try:
                await asyncio.sleep(10)
                key = TenantNamespace.cluster_key("nodes", self._node_id)
                running_count = sum(1 for t in self._local_tasks.values() if t.status == TaskStatus.RUNNING)
                await self._state._redis.hset(
                    key,
                    mapping={
                        "heartbeat": datetime.now().isoformat(),
                        "tasks_running": str(running_count),
                    },
                )
                await self._state._redis.expire(key, 60)
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    async def _retry_loop(self):
        while self._running:
            try:
                await asyncio.sleep(30)
                await self._process_retries()
            except Exception as e:
                logger.error(f"Retry loop error: {e}")

    async def _process_retries(self):
        for tenant_id in await self._list_active_tenants():
            ns = TenantNamespace(tenant_id)
            dlq_key = ns.queue_key("task:dlq")
            pending_key = ns.queue_key("task:pending")
            failed_tasks = await self._state._redis.zrangebyscore(dlq_key, "-inf", "+inf", withscores=True)
            for task_id_score in failed_tasks:
                task_id = task_id_score[0]
                task_data = await self._state._redis.hgetall(f"{ns.key('task')}:{task_id}")
                if not task_data:
                    continue
                task = self._dict_to_task(task_data)
                if task.retry_count < task.max_retries:
                    task.status = TaskStatus.PENDING
                    task.error = None
                    await self._state._redis.zrem(dlq_key, task_id)
                    await self._state._redis.zadd(pending_key, {task_id: task.priority.value})
                    logger.info(f"Task {task_id} requeued for retry {task.retry_count + 1}/{task.max_retries}")

    async def _list_active_tenants(self) -> List[str]:
        tenants = set()
        async for key in self._state._redis.scan_iter(match="wanclaw:tenant:*"):
            match = key.split(":")
            if len(match) >= 3:
                tenants.add(match[2])
        return list(tenants)

    async def submit_task(
        self,
        tenant_id: str,
        task_type: str,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
        metadata: Dict[str, Any] = None,
    ) -> str:
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        task = Task(
            task_id=task_id,
            tenant_id=tenant_id,
            task_type=task_type,
            payload=payload,
            priority=priority,
            max_retries=max_retries,
            metadata=metadata or {},
        )
        ns = TenantNamespace(tenant_id)
        task_key = ns.task_key(task_id)
        task_hash = self._task_to_dict(task)
        await self._state._redis.hset(task_key, mapping=task_hash)
        await self._state._redis.expire(task_key, 86400 * 7)
        pending_key = ns.queue_key("task:pending")
        await self._state._redis.zadd(pending_key, {task_id: priority.value})
        logger.info(f"Task submitted: {task_id} type={task_type} tenant={tenant_id}")
        return task_id

    async def get_task(self, task_id: str, tenant_id: str) -> Optional[Task]:
        ns = TenantNamespace(tenant_id)
        task_key = ns.task_key(task_id)
        data = await self._state._redis.hgetall(task_key)
        if not data:
            return None
        return self._dict_to_task(data)

    async def claim_task(self, tenant_id: str) -> Optional[Task]:
        ns = TenantNamespace(tenant_id)
        pending_key = ns.queue_key("task:pending")
        running_key = ns.queue_key("task:running")
        async with self._state.pipeline() as pipe:
            try:
                result = await self._state._redis.zrangebyscore(pending_key, "-inf", "+inf", withscores=True, start=0, num=1)
                if not result:
                    return None
                task_id = result[0][0]
                score = result[0][1]
                pipe.zrem(pending_key, task_id)
                pipe.zadd(running_key, {task_id: score})
                await pipe.execute()
                task = await self.get_task(task_id, tenant_id)
                if task:
                    task.status = TaskStatus.RUNNING
                    task.assigned_node = self._node_id
                    task.started_at = datetime.now()
                    await self._update_task(task)
                    self._local_tasks[task_id] = task
                    logger.info(f"Task claimed: {task_id} by {self._node_id}")
                return task
            except Exception as e:
                logger.error(f"Claim task error: {e}")
                return None

    async def update_progress(self, task_id: str, tenant_id: str, progress: float, checkpoint: Dict[str, Any] = None) -> bool:
        task = await self.get_task(task_id, tenant_id)
        if not task:
            return False
        task.progress = min(1.0, max(0.0, progress))
        if checkpoint:
            task.checkpoint = checkpoint
        ns = TenantNamespace(tenant_id)
        task_key = ns.task_key(task_id)
        await self._state._redis.hset(task_key, "progress", str(task.progress))
        if task.checkpoint:
            import json
            await self._state._redis.hset(task_key, "checkpoint", json.dumps(task.checkpoint, default=str))
        return True

    async def complete_task(self, task_id: str, tenant_id: str, result: Any = None) -> bool:
        task = await self.get_task(task_id, tenant_id)
        if not task:
            return False
        task.status = TaskStatus.COMPLETED
        task.result = result
        task.completed_at = datetime.now()
        task.progress = 1.0
        ns = TenantNamespace(tenant_id)
        task_key = ns.task_key(task_id)
        running_key = ns.queue_key("task:running")
        await self._update_task(task)
        await self._state._redis.zrem(running_key, task_id)
        self._local_tasks.pop(task_id, None)
        logger.info(f"Task completed: {task_id}")
        return True

    async def fail_task(self, task_id: str, tenant_id: str, error: str) -> bool:
        task = await self.get_task(task_id, tenant_id)
        if not task:
            return False
        task.error = error
        task.retry_count += 1
        ns = TenantNamespace(tenant_id)
        task_key = ns.task_key(task_id)
        running_key = ns.queue_key("task:running")
        dlq_key = ns.queue_key("task:dlq")
        if task.retry_count >= task.max_retries:
            task.status = TaskStatus.FAILED
            await self._state._redis.zrem(running_key, task_id)
            await self._state._redis.zadd(dlq_key, {task_id: task.priority.value})
            logger.warning(f"Task moved to DLQ: {task_id} after {task.retry_count} retries")
        else:
            task.status = TaskStatus.PENDING
            task.checkpoint = None
            await self._state._redis.zrem(running_key, task_id)
            pending_key = ns.queue_key("task:pending")
            await self._state._redis.zadd(pending_key, {task_id: task.priority.value})
            logger.warning(f"Task retry: {task_id} retry={task.retry_count}")
        await self._update_task(task)
        self._local_tasks.pop(task_id, None)
        return True

    async def cancel_task(self, task_id: str, tenant_id: str) -> bool:
        task = await self.get_task(task_id, tenant_id)
        if not task:
            return False
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now()
        ns = TenantNamespace(tenant_id)
        task_key = ns.task_key(task_id)
        running_key = ns.queue_key("task:running")
        pending_key = ns.queue_key("task:pending")
        await self._state._redis.zrem(running_key, task_id)
        await self._state._redis.zrem(pending_key, task_id)
        await self._update_task(task)
        self._local_tasks.pop(task_id, None)
        return True

    async def migrate_task(self, task_id: str, tenant_id: str, target_node_id: str) -> bool:
        task = await self.get_task(task_id, tenant_id)
        if not task or task.status not in (TaskStatus.PENDING, TaskStatus.ASSIGNED):
            return False
        task.assigned_node = target_node_id
        await self._update_task(task)
        await self.publish_task_event(tenant_id, "task_migrated", {"task_id": task_id, "from": self._node_id, "to": target_node_id})
        logger.info(f"Task {task_id} migrated from {self._node_id} to {target_node_id}")
        return True

    async def get_node_tasks(self, tenant_id: str) -> List[Task]:
        ns = TenantNamespace(tenant_id)
        running_key = ns.queue_key("task:running")
        task_ids = await self._state._redis.zrange(running_key, 0, -1)
        tasks = []
        for task_id in task_ids:
            task_data = await self._state._redis.hgetall(f"{ns.key('task')}:{task_id}")
            if task_data and task_data.get("assigned_node") == self._node_id:
                tasks.append(self._dict_to_task(task_data))
        return tasks

    async def list_tasks(
        self,
        tenant_id: str,
        status: TaskStatus = None,
        limit: int = 100,
    ) -> List[Task]:
        ns = TenantNamespace(tenant_id)
        tasks = []
        async for key in self._state._redis.scan_iter(match=ns.key("task:task-*")):
            task_data = await self._state._redis.hgetall(key)
            if task_data:
                task = self._dict_to_task(task_data)
                if status is None or task.status == status:
                    tasks.append(task)
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)[:limit]

    async def subscribe_task_events(self, tenant_id: str, handler: Callable[[str, Dict], None]):
        channel = f"task_events_{tenant_id}"
        await self._state.subscribe(channel, handler, tenant_id=None)

    async def publish_task_event(self, tenant_id: str, event_type: str, data: Dict[str, Any]):
        message = {"type": event_type, "tenant_id": tenant_id, "data": data, "timestamp": datetime.now().isoformat()}
        channel = f"task_events_{tenant_id}"
        await self._state.publish(channel, message, tenant_id=None)

    async def _update_task(self, task: Task):
        ns = TenantNamespace(task.tenant_id)
        task_key = ns.task_key(task.task_id)
        await self._state._redis.hset(task_key, mapping=self._task_to_dict(task))
        await self._state._redis.expire(task_key, 86400 * 7)

    def _task_to_dict(self, task: Task) -> Dict[str, str]:
        import json
        return {
            "task_id": task.task_id,
            "tenant_id": task.tenant_id,
            "task_type": task.task_type,
            "payload": json.dumps(task.payload, default=str),
            "priority": str(task.priority.value),
            "status": task.status.value,
            "assigned_node": task.assigned_node or "",
            "progress": str(task.progress),
            "checkpoint": json.dumps(task.checkpoint, default=str) if task.checkpoint else "",
            "retry_count": str(task.retry_count),
            "max_retries": str(task.max_retries),
            "error": task.error or "",
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else "",
            "completed_at": task.completed_at.isoformat() if task.completed_at else "",
            "metadata": json.dumps(task.metadata, default=str),
        }

    def _dict_to_task(self, data: Dict[str, str]) -> Task:
        import json
        payload = data.get("payload", "{}")
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except (json.JSONDecodeError, TypeError):
                payload = {}
        checkpoint = data.get("checkpoint", "")
        if checkpoint:
            try:
                checkpoint = json.loads(checkpoint)
            except (json.JSONDecodeError, TypeError):
                checkpoint = None
        metadata = data.get("metadata", "{}")
        if metadata:
            try:
                metadata = json.loads(metadata)
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        created_at = data.get("created_at", "")
        if isinstance(created_at, str) and created_at:
            created_at = datetime.fromisoformat(created_at)
        else:
            created_at = datetime.now()
        started_at = data.get("started_at", "")
        if isinstance(started_at, str) and started_at:
            started_at = datetime.fromisoformat(started_at)
        else:
            started_at = None
        completed_at = data.get("completed_at", "")
        if isinstance(completed_at, str) and completed_at:
            completed_at = datetime.fromisoformat(completed_at)
        else:
            completed_at = None
        return Task(
            task_id=data.get("task_id", ""),
            tenant_id=data.get("tenant_id", ""),
            task_type=data.get("task_type", ""),
            payload=payload,
            priority=TaskPriority(int(data.get("priority", 5))),
            status=TaskStatus(data.get("status", "pending")) if data.get("status") else TaskStatus.PENDING,
            assigned_node=data.get("assigned_node") or None,
            progress=float(data.get("progress", 0)),
            checkpoint=checkpoint,
            retry_count=int(data.get("retry_count", 0)),
            max_retries=int(data.get("max_retries", 3)),
            error=data.get("error") or None,
            created_at=created_at,
            started_at=started_at,
            completed_at=completed_at,
            metadata=metadata,
        )


_task_coordinator: Optional[CrossNodeTaskCoordinator] = None


async def get_task_coordinator() -> CrossNodeTaskCoordinator:
    global _task_coordinator
    if _task_coordinator is None:
        _task_coordinator = CrossNodeTaskCoordinator()
        await _task_coordinator.initialize()
    return _task_coordinator
