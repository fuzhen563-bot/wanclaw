"""
WanClaw Spawn & Report

Sub-agent system for parallel task execution.
Inspired by OpenClaw's spawn-and-report pattern.
"""

import asyncio
import logging
import time
import uuid
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class SubAgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SubAgent:
    agent_id: str
    label: str
    task: Dict
    model: str = "default"
    status: SubAgentStatus = SubAgentStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: float = 0
    completed_at: float = 0
    parent_id: Optional[str] = None


class SubAgentManager:
    def __init__(self, llm_client=None, max_agents: int = 10):
        self.agents: Dict[str, SubAgent] = {}
        self.llm = llm_client
        self.max_agents = max_agents
        self._running = False
        self._tasks: Dict[str, asyncio.Task] = {}
        self._on_complete: Dict[str, Callable] = {}

    def spawn(self, label: str, task: Dict, model: str = "default",
              parent_id: str = None, on_complete: Callable = None) -> str:
        if len(self.agents) >= self.max_agents:
            raise Exception(f"Max sub-agents ({self.max_agents}) reached")
        agent_id = f"sub_{uuid.uuid4().hex[:8]}"
        agent = SubAgent(
            agent_id=agent_id,
            label=label,
            task=task,
            model=model,
            parent_id=parent_id,
        )
        self.agents[agent_id] = agent
        if on_complete:
            self._on_complete[agent_id] = on_complete
        self._tasks[agent_id] = asyncio.create_task(self._run_agent(agent))
        logger.info(f"Sub-agent spawned: {label} ({agent_id})")
        return agent_id

    async def _run_agent(self, agent: SubAgent):
        agent.status = SubAgentStatus.RUNNING
        agent.started_at = time.time()
        try:
            if self.llm:
                messages = [
                    {"role": "system", "content": f"You are a sub-agent tasked with: {agent.label}. Complete the task and report results."},
                    {"role": "user", "content": json.dumps(agent.task, ensure_ascii=False)},
                ]
                response = await self.llm.chat(messages)
                agent.result = response.get("text", "")
            else:
                await asyncio.sleep(1)
                agent.result = f"Task '{agent.label}' completed (no LLM configured)"
            agent.status = SubAgentStatus.COMPLETED
        except Exception as e:
            agent.error = str(e)
            agent.status = SubAgentStatus.FAILED
            logger.error(f"Sub-agent {agent.agent_id} failed: {e}")
        finally:
            agent.completed_at = time.time()
            if agent.agent_id in self._on_complete:
                callback = self._on_complete.pop(agent.agent_id)
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(agent)
                    else:
                        callback(agent)
                except Exception as e:
                    logger.error(f"Callback for {agent.agent_id} failed: {e}")

    def stop(self, agent_id: str) -> bool:
        agent = self.agents.get(agent_id)
        if agent and agent.status == SubAgentStatus.RUNNING:
            task = self._tasks.get(agent_id)
            if task:
                task.cancel()
            agent.status = SubAgentStatus.CANCELLED
            agent.completed_at = time.time()
            logger.info(f"Sub-agent stopped: {agent_id}")
            return True
        return False

    def get_agent(self, agent_id: str) -> Optional[SubAgent]:
        return self.agents.get(agent_id)

    def list_agents(self, status: SubAgentStatus = None) -> List[Dict]:
        result = []
        for agent in self.agents.values():
            if status and agent.status != status:
                continue
            result.append({
                "id": agent.agent_id,
                "label": agent.label,
                "status": agent.status.value,
                "task": agent.task,
                "result_preview": str(agent.result)[:200] if agent.result else None,
                "error": agent.error,
                "created_at": agent.created_at,
                "started_at": agent.started_at,
                "completed_at": agent.completed_at,
                "duration": round(agent.completed_at - agent.started_at, 2) if agent.completed_at and agent.started_at else 0,
                "parent_id": agent.parent_id,
            })
        return result

    def cleanup(self, max_age_seconds: int = 3600):
        now = time.time()
        to_remove = []
        for agent_id, agent in self.agents.items():
            if agent.status in (SubAgentStatus.COMPLETED, SubAgentStatus.FAILED, SubAgentStatus.CANCELLED):
                if agent.completed_at and now - agent.completed_at > max_age_seconds:
                    to_remove.append(agent_id)
        for agent_id in to_remove:
            del self.agents[agent_id]
            if agent_id in self._tasks:
                del self._tasks[agent_id]

    def get_stats(self) -> Dict:
        status_counts = {}
        for agent in self.agents.values():
            s = agent.status.value
            status_counts[s] = status_counts.get(s, 0) + 1
        return {
            "total": len(self.agents),
            "max": self.max_agents,
            "by_status": status_counts,
        }


_sub_agent_mgr: Optional[SubAgentManager] = None


def get_sub_agent_manager(**kwargs) -> SubAgentManager:
    global _sub_agent_mgr
    if _sub_agent_mgr is None:
        _sub_agent_mgr = SubAgentManager(**kwargs)
    return _sub_agent_mgr
