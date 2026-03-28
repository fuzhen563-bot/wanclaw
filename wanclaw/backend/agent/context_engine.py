from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, TYPE_CHECKING
import asyncio
import logging
import time

from wanclaw.backend.agent.tokenizer import count_tokens

if TYPE_CHECKING:
    from wanclaw.backend.agent.context import TokenBudget

logger = logging.getLogger(__name__)


class ContextEnginePlugin(ABC):
    async def bootstrap(self, session_key: str, agent_config: Dict) -> Dict:
        return {"session_key": session_key, "bootstrap_items": []}

    async def ingest(self, session_key: str, message: Dict) -> Dict:
        return {"stored": True}

    async def assemble(self, session_key: str, system_prompt: str, recent_messages: List[Dict]) -> List[Dict]:
        return recent_messages

    @abstractmethod
    async def compact(self, messages: List[Dict], budget: "TokenBudget") -> List[Dict]:
        raise NotImplementedError

    @abstractmethod
    async def afterTurn(self, messages: List[Dict], turn_result: Dict) -> List[Dict]:
        raise NotImplementedError

    async def prepareSubagentSpawn(self, parent_session: str, subagent_config: Dict) -> Dict:
        return {"approved": True, "subagent_session": f"{parent_session}:sub"}

    async def onSubagentEnded(self, parent_session: str, subagent_result: Dict):
        pass

    def get_stats(self) -> Dict:
        return {"engine": type(self).__name__}


class DefaultContextEngine(ContextEnginePlugin):
    def __init__(self, max_tokens: int = 200000, warn_ratio: float = 0.20):
        self.max_tokens = max_tokens
        self.warn_tokens = max(8000, int(max_tokens * warn_ratio))
        self._compaction_count = 0
        self._pruning_count = 0

    def _est(self, text: str) -> int:
        from wanclaw.backend.agent.tokenizer import count_tokens as _ct
        return _ct(text)

    async def bootstrap(self, session_key: str, agent_config: Dict) -> Dict:
        return {"session_key": session_key, "bootstrap_items": []}

    async def ingest(self, session_key: str, message: Dict) -> Dict:
        return {"stored": True}

    async def assemble(self, session_key: str, system_prompt: str, recent_messages: List[Dict]) -> List[Dict]:
        return recent_messages

    async def compact(self, messages: List[Dict], budget: "TokenBudget") -> List[Dict]:
        if not messages:
            return messages
        total = sum(count_tokens(m.get("content", "")) for m in messages)
        if total <= self.warn_tokens:
            return messages
        keep = max(4, int(len(messages) * 0.6))
        if len(messages) <= keep:
            return messages
        first = 2
        last = keep - first - 1
        result = messages[:first]
        result.append({"role": "system", "content": f"[{len(messages) - first - last} 条已压缩]", "timestamp": time.time(), "compacted": True})
        result.extend(messages[-last:])
        self._compaction_count += 1
        logger.info(f"Compacted {len(messages)} → {len(result)} messages")
        return result

    async def afterTurn(self, messages: List[Dict], turn_result: Dict) -> List[Dict]:
        return messages

    async def prepareSubagentSpawn(self, parent_session: str, subagent_config: Dict) -> Dict:
        return {"approved": True, "subagent_session": f"{parent_session}:sub"}

    async def onSubagentEnded(self, parent_session: str, subagent_result: Dict):
        pass

    def get_stats(self) -> Dict:
        return {"engine": "DefaultContextEngine", "compactions": self._compaction_count}


class ContinuityContextEngine(ContextEnginePlugin):
    def __init__(self, memory_system=None):
        self.memory = memory_system
        self._facts: List[str] = []
        self._preferences: List[str] = []
        self._decisions: List[str] = []
        self._default_engine = DefaultContextEngine()

    async def bootstrap(self, session_key: str, agent_config: Dict) -> Dict:
        items = []
        if self._facts:
            items.append({"type": "fact", "content": "\n".join(self._facts[-5:])})
        if self._preferences:
            items.append({"type": "preference", "content": "\n".join(self._preferences[-5:])})
        if self._decisions:
            items.append({"type": "decision", "content": "\n".join(self._decisions[-5:])})
        return {"session_key": session_key, "bootstrap_items": items}

    async def ingest(self, session_key: str, message: Dict) -> Dict:
        content = message.get("content", "")
        role = message.get("role", "")
        if role == "user" and any(k in content.lower() for k in ["我", "i prefer", "i like", "always"]):
            self._preferences.append(content)
        return {"stored": True}

    async def assemble(self, session_key: str, system_prompt: str, recent_messages: List[Dict]) -> List[Dict]:
        return recent_messages

    async def compact(self, messages: List[Dict], budget: "TokenBudget") -> List[Dict]:
        return await self._default_engine.compact(messages, budget)

    async def afterTurn(self, messages: List[Dict], turn_result: Dict) -> List[Dict]:
        for msg in messages:
            c = msg.get("content", "")
            if msg.get("role") == "assistant" and any(d in c for d in ["决定", "decided", "will", "应该"]):
                self._decisions.append(c[:200])
        return messages

    async def prepareSubagentSpawn(self, parent_session: str, subagent_config: Dict) -> Dict:
        return {"approved": True, "subagent_session": f"{parent_session}:sub", "continuity": {}}

    async def onSubagentEnded(self, parent_session: str, subagent_result: Dict):
        pass

    def get_stats(self) -> Dict:
        return {"engine": "ContinuityContextEngine", "facts": len(self._facts), "decisions": len(self._decisions)}


_engine: Optional[ContextEnginePlugin] = None


def get_context_engine() -> ContextEnginePlugin:
    global _engine
    if _engine is None:
        _engine = DefaultContextEngine()
    return _engine


def set_context_engine(engine: ContextEnginePlugin):
    global _engine
    _engine = engine
