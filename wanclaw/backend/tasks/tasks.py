"""
Celery任务队列模块
支持异步执行、重试机制、断点续传
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
import hashlib

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    LOW = 0
    NORMAL = 5
    HIGH = 10
    URGENT = 20


@dataclass
class Task:
    task_id: str
    name: str
    payload: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    checkpoint: Optional[Dict[str, Any]] = None
    progress: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Checkpoint:
    task_id: str
    step: int
    data: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)


class TaskQueue:
    """异步任务队列（基于Redis Streams）"""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        queue_name: str = "wanclaw_tasks",
        task_ttl: int = 3600,
    ):
        self.redis_url = redis_url
        self.queue_name = queue_name
        self.task_ttl = task_ttl
        self.redis: Optional[aioredis.Redis] = None
        self._running = False

    async def connect(self):
        """连接Redis"""
        self.redis = await aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info(f"Task Queue connected: {self.queue_name}")

    async def close(self):
        """关闭连接"""
        if self.redis:
            await self.redis.close()

    async def enqueue(
        self,
        name: str,
        payload: Dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
        metadata: Dict[str, Any] = None,
    ) -> str:
        """入队"""
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        
        task = Task(
            task_id=task_id,
            name=name,
            payload=payload,
            priority=priority,
            max_retries=max_retries,
            metadata=metadata or {},
        )
        
        # 存储任务详情
        task_key = f"{self.queue_name}:task:{task_id}"
        await self.redis.hset(task_key, mapping=self._task_to_dict(task))
        await self.redis.expire(task_key, 86400)  # 24小时
        
        # 加入优先队列
        score = priority.value + task.created_at.timestamp()
        await self.redis.zadd(f"{self.queue_name}:pending", {task_id: score})
        
        logger.info(f"Task enqueued: {task_id} ({name})")
        return task_id

    async def dequeue(self, count: int = 1) -> List[Task]:
        """出队 — atomic dequeue with Redis pipeline + WATCH."""
        pending_key = f"{self.queue_name}:pending"
        running_key = f"{self.queue_name}:running"

        await self._cleanup_stale_tasks()

        for _ in range(count):
            max_retries_attempts = 5
            for attempt in range(max_retries_attempts):
                try:
                    async with self.redis.pipeline(transaction=True) as pipe:
                        pipe.zpopmin(pending_key, 1)
                        _, [[task_id, score]] = await pipe.execute()

                    if not task_id:
                        break

                    task = await self.get_task(task_id)
                    if not task:
                        logger.warning(f"Dequeued ghost task_id={task_id}, skipping")
                        continue

                    task.status = TaskStatus.RUNNING
                    task.started_at = datetime.now()
                    await self._save_task(task)

                    async with self.redis.pipeline(transaction=True) as pipe:
                        pipe.zadd(running_key, {task_id: task.started_at.timestamp()})
                        pipe.expire(f"{self.queue_name}:task:{task_id}", max(self.task_ttl * 2, 86400))
                        await pipe.execute()

                    return [task]

                except aioredis.WatchError:
                    if attempt < max_retries_attempts - 1:
                        await asyncio.sleep(0.01 * (2 ** attempt))
                        continue
                    logger.warning("dequeue: WATCH error exceeded retries, giving up")
                    break
                except (ValueError, TypeError):
                    break

        return []

    async def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        task_key = f"{self.queue_name}:task:{task_id}"
        data = await self.redis.hgetall(task_key)
        if not data:
            return None
        return self._dict_to_task(data)

    async def complete(self, task_id: str, result: Any = None):
        """完成任务"""
        task = await self.get_task(task_id)
        if task:
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result
            task.progress = 1.0
            await self._save_task(task)
            
            # 从运行队列移除
            await self.redis.zrem(f"{self.queue_name}:running", task_id)
            
            logger.info(f"Task completed: {task_id}")

    async def fail(self, task_id: str, error: str):
        """任务失败"""
        task = await self.get_task(task_id)
        if task:
            task.retry_count += 1
            
            if task.retry_count < task.max_retries:
                task.status = TaskStatus.RETRY
                task.error = f"{error} (retry {task.retry_count}/{task.max_retries})"
                # 延迟重试
                delay = min(60 * (2 ** task.retry_count), 3600)
                retry_time = datetime.now() + timedelta(seconds=delay)
                await self.redis.zadd(
                    f"{self.queue_name}:pending",
                    {task_id: retry_time.timestamp()}
                )
            else:
                task.status = TaskStatus.FAILED
                task.error = error
                task.completed_at = datetime.now()
                await self.redis.zadd(
                    f"{self.queue_name}:dlq",
                    {task_id: datetime.now().timestamp()}
                )
            
            await self._save_task(task)
            await self.redis.zrem(f"{self.queue_name}:running", task_id)
            
            logger.warning(f"Task failed: {task_id} - {error}")

    async def cancel(self, task_id: str):
        """取消任务"""
        task = await self.get_task(task_id)
        if task:
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            await self._save_task(task)
            await self.redis.zrem(f"{self.queue_name}:pending", task_id)
            await self.redis.zrem(f"{self.queue_name}:running", task_id)

    async def update_progress(self, task_id: str, progress: float, checkpoint: Dict[str, Any] = None):
        """更新进度"""
        task = await self.get_task(task_id)
        if task:
            task.progress = min(progress, 1.0)
            if checkpoint:
                task.checkpoint = checkpoint
                await self._save_checkpoint(task_id, checkpoint)
            await self._save_task(task)

    async def get_task_status(self, task_id: str) -> Optional[Task]:
        """获取任务状态"""
        return await self.get_task(task_id)

    async def list_tasks(self, status: TaskStatus = None, limit: int = 100) -> List[Task]:
        """列出任务"""
        tasks = []
        if status == TaskStatus.PENDING:
            task_ids = await self.redis.zrange(f"{self.queue_name}:pending", 0, limit - 1)
        elif status == TaskStatus.RUNNING:
            task_ids = await self.redis.zrange(f"{self.queue_name}:running", 0, limit - 1)
        else:
            pattern = f"{self.queue_name}:task:*"
            task_ids = []
            async for key in self.redis.scan_iter(match=pattern):
                task_id = key.split(":")[-1]
                task_ids.append(task_id)
        
        for task_id in task_ids:
            task = await self.get_task(task_id)
            if task and (status is None or task.status == status):
                tasks.append(task)
        
        return tasks

    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        pending = await self.redis.zcard(f"{self.queue_name}:pending")
        running = await self.redis.zcard(f"{self.queue_name}:running")
        dlq_size = await self.redis.zcard(f"{self.queue_name}:dlq")
        
        completed = 0
        failed = 0
        pattern = f"{self.queue_name}:task:*"
        async for key in self.redis.scan_iter(match=pattern):
            data = await self.redis.hgetall(key)
            if data:
                status = data.get("status")
                if status == "completed":
                    completed += 1
                elif status == "failed":
                    failed += 1
        
        return {
            "pending": pending,
            "running": running,
            "completed": completed,
            "failed": failed,
            "dlq_size": dlq_size,
            "total": pending + running + completed + failed,
        }

    async def get_dlq(self, limit: int = 100) -> List[Task]:
        """Retrieve dead-letter tasks ordered by failed_at timestamp (oldest first)."""
        dlq_key = f"{self.queue_name}:dlq"
        task_ids = await self.redis.zrange(dlq_key, 0, limit - 1)
        tasks = []
        for task_id in task_ids:
            task = await self.get_task(task_id)
            if task:
                tasks.append(task)
        return tasks

    async def requeue_dlq(self, task_id: str) -> bool:
        """Move a DLQ task back to pending queue. Returns True if found and requeued."""
        task = await self.get_task(task_id)
        if not task or task.status != TaskStatus.FAILED:
            return False

        await self.redis.zrem(f"{self.queue_name}:dlq", task_id)

        task.status = TaskStatus.PENDING
        task.retry_count = 0
        task.error = None
        task.completed_at = None
        score = task.priority.value + datetime.now().timestamp()
        await self._save_task(task)
        await self.redis.zadd(f"{self.queue_name}:pending", {task_id: score})

        logger.info(f"DLQ requeue: {task_id} returned to pending")
        return True

    async def cleanup_completed(self, older_than_hours: int = 24):
        """清理已完成任务"""
        pattern = f"{self.queue_name}:task:*"
        cutoff = datetime.now() - timedelta(hours=older_than_hours)
        
        async for key in self.redis.scan_iter(match=pattern):
            data = await self.redis.hgetall(key)
            if data and data.get("status") == "completed":
                completed_at = data.get("completed_at")
                if completed_at:
                    if datetime.fromisoformat(completed_at) < cutoff:
                        task_id = key.split(":")[-1]
                        await self.redis.delete(key)

    def _task_to_dict(self, task: Task) -> Dict[str, Any]:
        return {
            "task_id": task.task_id,
            "name": task.name,
            "payload": json.dumps(task.payload),
            "status": task.status.value,
            "priority": str(task.priority.value),
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else "",
            "completed_at": task.completed_at.isoformat() if task.completed_at else "",
            "result": json.dumps(task.result) if task.result else "",
            "error": task.error or "",
            "retry_count": str(task.retry_count),
            "max_retries": str(task.max_retries),
            "checkpoint": json.dumps(task.checkpoint) if task.checkpoint else "",
            "progress": str(task.progress),
            "metadata": json.dumps(task.metadata),
        }

    def _dict_to_task(self, data: Dict[str, Any]) -> Task:
        return Task(
            task_id=data["task_id"],
            name=data["name"],
            payload=json.loads(data["payload"]),
            status=TaskStatus(data["status"]),
            priority=TaskPriority(int(data.get("priority", 5))),
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            result=json.loads(data["result"]) if data.get("result") else None,
            error=data.get("error"),
            retry_count=int(data.get("retry_count", 0)),
            max_retries=int(data.get("max_retries", 3)),
            checkpoint=json.loads(data["checkpoint"]) if data.get("checkpoint") else None,
            progress=float(data.get("progress", 0)),
            metadata=json.loads(data.get("metadata", "{}")),
        )

    async def _save_task(self, task: Task):
        """保存任务"""
        key = f"{self.queue_name}:task:{task.task_id}"
        await self.redis.hset(key, mapping=self._task_to_dict(task))

    async def _save_checkpoint(self, task_id: str, checkpoint: Dict[str, Any]):
        """保存断点"""
        key = f"{self.queue_name}:checkpoint:{task_id}"
        await self.redis.hset(key, mapping={
            "task_id": task_id,
            "data": json.dumps(checkpoint),
            "created_at": datetime.now().isoformat(),
        })
        await self.redis.expire(key, 86400)

    async def get_checkpoint(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取断点"""
        key = f"{self.queue_name}:checkpoint:{task_id}"
        data = await self.redis.hgetall(key)
        if data:
            return json.loads(data["data"])
        return None

    async def _cleanup_stale_tasks(self):
        """Mark RUNNING tasks older than task_ttl as FAILED and move them to DLQ."""
        running_key = f"{self.queue_name}:running"
        now = datetime.now().timestamp()
        cutoff = now - self.task_ttl

        # Fetch all running tasks whose started_at score is below cutoff
        stale_task_ids = await self.redis.zrangebyscore(
            running_key, "-inf", cutoff
        )

        for task_id in stale_task_ids:
            task = await self.get_task(task_id)
            if task and task.status == TaskStatus.RUNNING:
                task.status = TaskStatus.FAILED
                task.error = f"Task timed out after {self.task_ttl}s (stale worker)"
                task.completed_at = datetime.now()
                await self._save_task(task)
                await self.redis.zrem(running_key, task_id)
                await self.redis.zadd(
                    f"{self.queue_name}:dlq",
                    {task_id: datetime.now().timestamp()}
                )
                logger.warning(
                    f"Stale task {task_id} marked FAILED and moved to DLQ "
                    f"(ran for {int(now - task.started_at.timestamp())}s)"
                )


class TaskExecutor:
    """任务执行器"""

    def __init__(
        self,
        queue: TaskQueue,
        worker_name: str = "worker-1",
        max_concurrent: int = 5,
        task_timeout: int = 300,
        heartbeat_interval: int = 30,
    ):
        self.queue = queue
        self.worker_name = worker_name
        self.handlers: Dict[str, Callable] = {}
        self._running = False
        self._max_concurrent = max_concurrent
        self._task_timeout = task_timeout
        self._heartbeat_interval = heartbeat_interval
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._heartbeat_task: Optional[asyncio.Task] = None

    def register(self, task_name: str):
        """注册任务处理器"""
        def decorator(func: Callable):
            self.handlers[task_name] = func
            return func
        return decorator

    async def start(self):
        """启动执行器"""
        self._running = True
        self._semaphore = asyncio.Semaphore(self._max_concurrent)
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        asyncio.create_task(self._run_loop())
        logger.info(
            f"Task Executor started: {self.worker_name} "
            f"(max_concurrent={self._max_concurrent}, "
            f"task_timeout={self._task_timeout}s, "
            f"heartbeat={self._heartbeat_interval}s)"
        )

    async def stop(self):
        """停止执行器"""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

    async def _heartbeat_loop(self):
        """Periodically reclaim stale tasks from dead workers."""
        while self._running:
            await asyncio.sleep(self._heartbeat_interval)
            try:
                await self._claim_stale_tasks()
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    async def _claim_stale_tasks(self):
        """Mark RUNNING tasks whose workers died as FAILED and move to DLQ."""
        await self.queue._cleanup_stale_tasks()

    async def _run_loop(self):
        """执行循环 — processes up to max_concurrent tasks in parallel."""
        while self._running:
            try:
                tasks = await self.queue.dequeue(count=self._max_concurrent)
                if not tasks:
                    await asyncio.sleep(0.1)
                    continue

                await asyncio.gather(
                    *(self._execute_task_with_semaphore(t) for t in tasks),
                    return_exceptions=False,
                )
            except Exception as e:
                logger.error(f"Execute loop error: {e}")
                await asyncio.sleep(1)

    async def _execute_task_with_semaphore(self, task: Task):
        """Execute a task while respecting the concurrency limit."""
        async with self._semaphore:
            await self._execute_task(task)

    async def _execute_task(self, task: Task):
        """执行单个任务"""
        logger.info(f"Executing task: {task.task_id} ({task.name})")
        
        try:
            checkpoint = task.checkpoint or await self.queue.get_checkpoint(task.task_id)
            if checkpoint:
                task.payload["_checkpoint"] = checkpoint
            
            handler = self.handlers.get(task.name)
            if handler:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(task.payload)
                else:
                    result = handler(task.payload)
            else:
                result = {"error": f"No handler for task: {task.name}"}
            
            await self.queue.complete(task.task_id, result)
            
        except Exception as e:
            logger.error(f"Task failed: {task.task_id} - {e}")
            await self.queue.fail(task.task_id, str(e))

    async def execute_now(self, name: str, payload: Dict[str, Any]) -> Task:
        """立即执行（不排队）"""
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        task = Task(task_id=task_id, name=name, payload=payload)
        
        try:
            handler = self.handlers.get(name)
            if handler:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(payload)
                else:
                    result = handler(payload)
                
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.completed_at = datetime.now()
            else:
                task.status = TaskStatus.FAILED
                task.error = f"No handler for task: {name}"
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
        
        return task


# 全局实例
_task_queue: Optional[TaskQueue] = None
_task_executor: Optional[TaskExecutor] = None


async def get_task_queue(
    redis_url: str = "redis://localhost:6379",
    queue_name: str = "wanclaw_tasks",
) -> TaskQueue:
    """获取任务队列单例"""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue(redis_url, queue_name)
        await _task_queue.connect()
    return _task_queue


async def get_task_executor(
    redis_url: str = "redis://localhost:6379",
    queue_name: str = "wanclaw_tasks",
    worker_name: str = "worker-1",
) -> TaskExecutor:
    """获取任务执行器单例"""
    global _task_executor
    if _task_executor is None:
        queue = await get_task_queue(redis_url, queue_name)
        _task_executor = TaskExecutor(queue, worker_name)
    return _task_executor


# 便捷装饰器
def task(name: str, priority: TaskPriority = TaskPriority.NORMAL, max_retries: int = 3):
    """任务装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            queue = await get_task_queue()
            task_id = await queue.enqueue(
                name=name,
                payload={"args": args, "kwargs": kwargs},
                priority=priority,
                max_retries=max_retries,
            )
            return task_id
        return wrapper
    return decorator
