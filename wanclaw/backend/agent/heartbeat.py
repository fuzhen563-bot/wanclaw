"""
WanClaw Heartbeat + Cron Scheduler

Proactive agent execution inspired by OpenClaw's heartbeat system.
Agent wakes up periodically, checks for pending tasks, and takes action.
"""

import asyncio
import logging
import time
import json
import re
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def _parse_cron_next(schedule: str, base: float = None) -> float:
    parts = schedule.split()
    if len(parts) < 5:
        return (base or time.time()) + 300
    minute_s, hour_s, day_s, month_s, dow_s = parts[:5]
    import datetime
    now = datetime.datetime.fromtimestamp(base or time.time())
    for delta in range(1, 1441):
        t = now + datetime.timedelta(minutes=delta)
        if minute_s != "*" and t.minute != int(minute_s):
            continue
        if hour_s != "*" and t.hour != int(hour_s):
            continue
        if day_s != "*" and t.day != int(day_s):
            continue
        if month_s != "*" and t.month != int(month_s):
            continue
        return t.timestamp()
    return (base or time.time()) + 3600


@dataclass
class CronJob:
    job_id: str
    name: str
    schedule: str
    handler: Callable
    args: Dict = field(default_factory=dict)
    enabled: bool = True
    last_run: float = 0
    next_run: float = 0
    run_count: int = 0


class CronScheduler:
    def __init__(self):
        self.jobs: Dict[str, CronJob] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def add_job(self, job_id: str, name: str, schedule: str, handler: Callable, args: Dict = None):
        try:
            next_run = _parse_cron_next(schedule)
            
        except Exception:
            next_run = time.time() + 300

        self.jobs[job_id] = CronJob(
            job_id=job_id,
            name=name,
            schedule=schedule,
            handler=handler,
            args=args or {},
            next_run=next_run,
        )
        logger.info(f"Cron job added: {name} ({schedule})")

    def remove_job(self, job_id: str):
        if job_id in self.jobs:
            del self.jobs[job_id]
            logger.info(f"Cron job removed: {job_id}")

    def enable_job(self, job_id: str):
        if job_id in self.jobs:
            self.jobs[job_id].enabled = True

    def disable_job(self, job_id: str):
        if job_id in self.jobs:
            self.jobs[job_id].enabled = False

    async def _run_loop(self):
        self._running = True
        logger.info("Cron scheduler started")
        while self._running:
            now = time.time()
            for job_id, job in list(self.jobs.items()):
                if not job.enabled:
                    continue
                if now >= job.next_run:
                    try:
                        logger.info(f"Running cron job: {job.name}")
                        if asyncio.iscoroutinefunction(job.handler):
                            await job.handler(**job.args)
                        else:
                            job.handler(**job.args)
                        job.last_run = now
                        job.run_count += 1
                        try:
                            job.next_run = _parse_cron_next(job.schedule)
                        except Exception:
                            job.next_run = now + 300
                    except Exception as e:
                        logger.error(f"Cron job {job.name} failed: {e}")
                        job.next_run = now + 60
            await asyncio.sleep(10)

    def start(self):
        if not self._running:
            self._task = asyncio.create_task(self._run_loop())

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    def get_jobs(self) -> List[Dict]:
        return [{
            "id": j.job_id,
            "name": j.name,
            "schedule": j.schedule,
            "enabled": j.enabled,
            "last_run": j.last_run,
            "next_run": j.next_run,
            "run_count": j.run_count,
        } for j in self.jobs.values()]


class Heartbeat:
    def __init__(self, agent_core=None, interval: int = 1800):
        self.agent = agent_core
        self.interval = interval
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.tick_count = 0
        self.last_tick: float = 0
        self.tasks: List[Dict] = []

    def add_task(self, name: str, prompt: str, schedule: str = None):
        self.tasks.append({"name": name, "prompt": prompt, "schedule": schedule, "enabled": True})

    async def _tick(self):
        self.tick_count += 1
        self.last_tick = time.time()
        logger.info(f"Heartbeat tick #{self.tick_count}")
        for task in self.tasks:
            if not task.get("enabled"):
                continue
            try:
                if self.agent:
                    result = await self.agent.think(task["prompt"], context=f"Heartbeat tick #{self.tick_count}")
                    logger.info(f"Heartbeat task '{task['name']}' completed: {result.result[:100]}")
            except Exception as e:
                logger.error(f"Heartbeat task '{task['name']}' failed: {e}")

    async def _run_loop(self):
        self._running = True
        logger.info(f"Heartbeat started (interval: {self.interval}s)")
        while self._running:
            await self._tick()
            await asyncio.sleep(self.interval)

    def start(self):
        if not self._running:
            self._task = asyncio.create_task(self._run_loop())

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    def get_status(self) -> Dict:
        return {
            "running": self._running,
            "interval": self.interval,
            "tick_count": self.tick_count,
            "last_tick": self.last_tick,
            "tasks": self.tasks,
        }


_cron: Optional[CronScheduler] = None
_heartbeat: Optional[Heartbeat] = None


def get_cron() -> CronScheduler:
    global _cron
    if _cron is None:
        _cron = CronScheduler()
    return _cron


def get_heartbeat(**kwargs) -> Heartbeat:
    global _heartbeat
    if _heartbeat is None:
        _heartbeat = Heartbeat(**kwargs)
    return _heartbeat
