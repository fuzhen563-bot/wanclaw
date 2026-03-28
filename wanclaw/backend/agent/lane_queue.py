"""
WanClaw Lane Queue

Two-level command queue inspired by OpenClaw's lane system.
Session lane (serial) + Global lane (capped concurrency).
Prevents concurrent agent runs from colliding.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class QueueMode(str, Enum):
    COLLECT = "collect"
    REJECT = "reject"
    QUEUE = "queue"


@dataclass
class QueueEntry:
    entry_id: str
    session_key: str
    payload: Dict
    handler: Callable
    enqueued_at: float = field(default_factory=time.time)
    warn_after_ms: float = 5000
    started_at: float = 0
    completed_at: float = 0
    status: str = "queued"
    result: Any = None
    error: Optional[str] = None


@dataclass
class LaneState:
    queue: List[QueueEntry] = field(default_factory=list)
    active_task_ids: List[str] = field(default_factory=list)
    max_concurrent: int = 1
    draining: bool = False
    generation: int = 0
    total_processed: int = 0
    total_failed: int = 0


class SessionLane:
    def __init__(self, session_key: str, max_concurrent: int = 1):
        self.session_key = session_key
        self.state = LaneState(max_concurrent=max_concurrent)

    async def enqueue(self, entry: QueueEntry) -> str:
        self.state.queue.append(entry)
        logger.debug(f"Session {self.session_key}: enqueued {entry.entry_id} (queue size: {len(self.state.queue)})")
        asyncio.create_task(self._drain())
        return entry.entry_id

    async def _drain(self):
        if self.state.draining:
            return
        self.state.draining = True
        try:
            while self.state.queue and len(self.state.active_task_ids) < self.state.max_concurrent:
                entry = self.state.queue.pop(0)
                if entry.status != "queued":
                    continue
                entry.status = "running"
                entry.started_at = time.time()
                self.state.active_task_ids.append(entry.entry_id)
                asyncio.create_task(self._execute(entry))
        finally:
            self.state.draining = False

    async def _execute(self, entry: QueueEntry):
        gen = self.state.generation
        try:
            if asyncio.iscoroutinefunction(entry.handler):
                result = await entry.handler(entry.payload)
            else:
                result = entry.handler(entry.payload)
            if gen == self.state.generation:
                entry.result = result
                entry.status = "completed"
                self.state.total_processed += 1
        except Exception as e:
            if gen == self.state.generation:
                entry.error = str(e)
                entry.status = "failed"
                self.state.total_failed += 1
                logger.error(f"Session {self.session_key}: task {entry.entry_id} failed: {e}")
        finally:
            entry.completed_at = time.time()
            if entry.entry_id in self.state.active_task_ids:
                self.state.active_task_ids.remove(entry.entry_id)
            asyncio.create_task(self._drain())

    def clear(self):
        for entry in self.state.queue:
            if entry.status == "queued":
                entry.status = "cancelled"
        self.state.queue = [e for e in self.state.queue if e.status == "queued"]

    def reset(self):
        self.state.generation += 1
        self.state.active_task_ids.clear()
        self.state.queue.clear()
        logger.info(f"Session {self.session_key}: reset (generation {self.state.generation})")

    def get_stats(self) -> Dict:
        return {
            "session_key": self.session_key,
            "queued": len(self.state.queue),
            "active": len(self.state.active_task_ids),
            "max_concurrent": self.state.max_concurrent,
            "total_processed": self.state.total_processed,
            "total_failed": self.state.total_failed,
            "generation": self.state.generation,
        }


class GlobalLane:
    def __init__(self, max_concurrent: int = 4):
        self.max_concurrent = max_concurrent
        self.session_lanes: Dict[str, SessionLane] = {}
        self._lock = asyncio.Lock()
        self.queue_mode = QueueMode.COLLECT

    def get_session_lane(self, session_key: str) -> SessionLane:
        if session_key not in self.session_lanes:
            self.session_lanes[session_key] = SessionLane(session_key)
        return self.session_lanes[session_key]

    async def enqueue(self, session_key: str, payload: Dict, handler: Callable) -> str:
        async with self._lock:
            active_global = sum(
                len(sl.state.active_task_ids)
                for sl in self.session_lanes.values()
            )
            if active_global >= self.max_concurrent:
                if self.queue_mode == QueueMode.REJECT:
                    raise Exception("Global concurrency limit reached")
        entry = QueueEntry(
            entry_id=str(uuid.uuid4())[:8],
            session_key=session_key,
            payload=payload,
            handler=handler,
        )
        lane = self.get_session_lane(session_key)
        return await lane.enqueue(entry)

    def cancel(self, session_key: str, entry_id: str) -> bool:
        lane = self.session_lanes.get(session_key)
        if lane:
            for entry in lane.state.queue:
                if entry.entry_id == entry_id:
                    entry.status = "cancelled"
                    lane.state.queue.remove(entry)
                    return True
        return False

    def get_stats(self) -> Dict:
        total_queued = sum(len(sl.state.queue) for sl in self.session_lanes.values())
        total_active = sum(len(sl.state.active_task_ids) for sl in self.session_lanes.values())
        return {
            "sessions": len(self.session_lanes),
            "global_max_concurrent": self.max_concurrent,
            "total_queued": total_queued,
            "total_active": total_active,
            "queue_mode": self.queue_mode.value,
            "sessions_stats": [sl.get_stats() for sl in self.session_lanes.values()],
        }


_global_lane: Optional[GlobalLane] = None


def get_global_lane(**kwargs) -> GlobalLane:
    global _global_lane
    if _global_lane is None:
        _global_lane = GlobalLane(**kwargs)
    return _global_lane
