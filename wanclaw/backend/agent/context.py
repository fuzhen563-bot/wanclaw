import logging
import time
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from wanclaw.backend.agent.tokenizer import count_tokens

logger = logging.getLogger(__name__)


@dataclass
class TokenBudget:
    total_tokens: int
    system_prompt_tokens: int = 0
    memory_tokens: int = 0
    history_tokens: int = 0
    tools_tokens: int = 0
    skills_tokens: int = 0
    reserved_tokens: int = 0

    @property
    def used_tokens(self) -> int:
        return (self.system_prompt_tokens + self.memory_tokens +
                self.history_tokens + self.tools_tokens + self.skills_tokens)

    @property
    def available_tokens(self) -> int:
        return self.total_tokens - self.used_tokens - self.reserved_tokens

    @property
    def usage_ratio(self) -> float:
        return self.used_tokens / self.total_tokens if self.total_tokens > 0 else 0

    def to_dict(self) -> Dict:
        return {
            "total": self.total_tokens,
            "system_prompt": self.system_prompt_tokens,
            "memory": self.memory_tokens,
            "history": self.history_tokens,
            "tools": self.tools_tokens,
            "skills": self.skills_tokens,
            "reserved": self.reserved_tokens,
            "used": self.used_tokens,
            "available": self.available_tokens,
            "usage_ratio": round(self.usage_ratio * 100, 1),
        }


def estimate_tokens(text: str) -> int:
    from wanclaw.backend.agent.tokenizer import count_tokens as _ct
    return _ct(text)


class ContextManager:
    def __init__(self, max_tokens: int = 200000, hard_min_ratio: float = 0.10, warn_ratio: float = 0.20,
                 engine: "ContextEnginePlugin" = None):
        self.max_tokens = max_tokens
        self.hard_min_tokens = max(4000, int(max_tokens * hard_min_ratio))
        self.warn_tokens = max(8000, int(max_tokens * warn_ratio))
        self.reserved_tokens = int(max_tokens * 0.10)
        self.budget = TokenBudget(total_tokens=max_tokens, reserved_tokens=self.reserved_tokens)
        self._compaction_count = 0
        self._pruning_count = 0
        if engine is None:
            from wanclaw.backend.agent.context_engine import get_context_engine
            engine = get_context_engine()
        self.engine = engine

    def update_budget(self, system_prompt: str = "", memory: str = "",
                       history: List[Dict] = None, tools: str = "",
                       skills: str = ""):
        self.budget.system_prompt_tokens = count_tokens(system_prompt)
        self.budget.memory_tokens = count_tokens(memory)
        self.budget.history_tokens = sum(count_tokens(m.get("content", "")) for m in (history or []))
        self.budget.tools_tokens = count_tokens(tools)
        self.budget.skills_tokens = count_tokens(skills)

    def needs_compaction(self) -> bool:
        return self.budget.available_tokens < self.warn_tokens

    def needs_pruning(self) -> bool:
        return self.budget.available_tokens < self.hard_min_tokens

    def compact_history(self, history: List[Dict], target_ratio: float = 0.6) -> List[Dict]:
        if not history:
            return history
        target_count = max(4, int(len(history) * target_ratio))
        if len(history) <= target_count:
            return history
        keep_first = 2
        keep_last = target_count - keep_first - 1
        compacted = history[:keep_first]
        compacted.append({
            "role": "system",
            "content": f"[{len(history) - keep_first - keep_last} 条消息已压缩]",
            "timestamp": time.time(),
            "compacted": True,
        })
        compacted.extend(history[-keep_last:])
        self._compaction_count += 1
        logger.info(f"Compacted {len(history)} messages to {len(compacted)}")
        return compacted

    def prune_tool_results(self, history: List[Dict], max_age_seconds: int = 3600) -> List[Dict]:
        now = time.time()
        pruned = []
        for msg in history:
            if msg.get("role") == "tool" and now - msg.get("timestamp", now) > max_age_seconds:
                pruned.append({**msg, "content": "[结果已清理]", "pruned": True})
                self._pruning_count += 1
            else:
                pruned.append(msg)
        if self._pruning_count > 0:
            logger.info(f"Pruned {self._pruning_count} old tool results")
        return pruned

    def get_lazy_skills(self, all_skills: List[Dict], user_input: str, max_skills: int = 5) -> List[Dict]:
        if not all_skills:
            return []
        input_lower = user_input.lower()
        scored = []
        for skill in all_skills:
            score = 0
            name = skill.get("name", "").lower()
            desc = skill.get("description", "").lower()
            tags = " ".join(skill.get("tags", [])).lower()
            if name in input_lower:
                score += 10
            for word in input_lower.split():
                if word in desc or word in tags:
                    score += 2
            scored.append((score, skill))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:max_skills]]

    def prepare_messages(self, system_prompt: str, history: List[Dict],
                          tools_desc: str = "", skills_desc: str = "") -> List[Dict]:
        self.update_budget(system_prompt=system_prompt, history=history,
                           tools=tools_desc, skills=skills_desc)
        processed = history
        if self.needs_pruning():
            processed = self.engine.prune(processed)
            self._pruning_count += 1
        if self.needs_compaction():
            processed = self.engine.compact(processed, self.budget)
            self._compaction_count += 1
        processed = self.engine.afterTurn(processed, {})
        messages = [{"role": "system", "content": system_prompt}]
        if tools_desc:
            messages.append({"role": "system", "content": f"Available tools:\n{tools_desc}"})
        if skills_desc:
            messages.append({"role": "system", "content": f"Available skills:\n{skills_desc}"})
        messages.extend(processed)
        return messages

    def get_stats(self) -> Dict:
        return {
            "max_tokens": self.max_tokens,
            "hard_min": self.hard_min_tokens,
            "warn_threshold": self.warn_tokens,
            "compaction_count": self._compaction_count,
            "pruning_count": self._pruning_count,
            "budget": self.budget.to_dict(),
            "engine": type(self.engine).__name__,
        }


_context_mgr: Optional[ContextManager] = None


def get_context_manager(**kwargs) -> ContextManager:
    global _context_mgr
    if _context_mgr is None:
        _context_mgr = ContextManager(**kwargs)
    return _context_mgr
