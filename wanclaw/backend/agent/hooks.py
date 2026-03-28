"""
WanClaw Hook System
Inspired by OpenClaw's two-tier hook architecture.
Plugin Hooks: before_agent_start/end, before/after_tool_call, before/after_llm_call,
  message_received/sending, session_start/end, gateway_start/stop, before_agent_reply,
  response:before_deliver, dispatch_interceptor.
Gateway Hooks: agent:bootstrap, /new, /reset, etc.
"""

import asyncio
import logging
import time
import re
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

import asyncio
from collections import OrderedDict

_approval_queue: OrderedDict = {}
_approval_id_counter = 0

def queue_approval(action: str, details: Dict, risk_level: str = "medium") -> str:
    global _approval_id_counter
    _approval_id_counter += 1
    aid = f"approval_{_approval_id_counter}"
    _approval_queue[aid] = {
        "id": aid, "action": action, "details": details,
        "risk_level": risk_level, "status": "pending",
        "created_at": time.time()
    }
    return aid

def get_pending_approvals() -> List[Dict]:
    return [v for v in _approval_queue.values() if v["status"] == "pending"]

def approve_action(aid: str) -> bool:
    if aid in _approval_queue:
        _approval_queue[aid]["status"] = "approved"
        return True
    return False

def reject_action(aid: str) -> bool:
    if aid in _approval_queue:
        _approval_queue[aid]["status"] = "rejected"
        return True
    return False


class HookEvent:
    GATEWAY_START = "gateway_start"
    GATEWAY_STOP = "gateway_stop"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_SENDING = "message_sending"
    BEFORE_AGENT_START = "before_agent_start"
    AGENT_END = "agent_end"
    BEFORE_LLM_CALL = "before_llm_call"
    AFTER_LLM_CALL = "after_llm_call"
    BEFORE_TOOL_CALL = "before_tool_call"
    AFTER_TOOL_CALL = "after_tool_call"
    BEFORE_AGENT_REPLY = "before_agent_reply"
    RESPONSE_BEFORE_DELIVER = "response:before_deliver"
    DISPATCH_INTERCEPTOR = "dispatch_interceptor"


GATEWAY_HOOK_EVENTS = [
    "agent:bootstrap", "agent:start", "agent:stop",
    "/new", "/reset", "/help", "/skill",
]


@dataclass
class HookContext:
    timestamp: float = field(default_factory=time.time)
    session_key: Optional[str] = None
    platform: Optional[str] = None
    channel_id: Optional[str] = None
    user_id: Optional[str] = None
    sender_name: Optional[str] = None
    sender_is_owner: bool = False
    group_id: Optional[str] = None
    spawned_by: Optional[str] = None
    message_provider: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class MessageHookContext(HookContext):
    message_id: Optional[str] = None
    content: str = ""
    message_type: str = "text"
    raw: Dict = field(default_factory=dict)


@dataclass
class AgentHookContext(HookContext):
    user_input: str = ""
    turn_id: Optional[str] = None
    thoughts: List[str] = field(default_factory=list)
    actions: List[Dict] = field(default_factory=list)
    result: str = ""
    status: str = "pending"


@dataclass
class LLMCallHookContext(HookContext):
    messages: List[Dict] = field(default_factory=list)
    system_prompt: str = ""
    model: str = ""
    tools: List[Dict] = field(default_factory=list)
    response: Optional[Dict] = None
    error: Optional[str] = None


@dataclass
class ToolCallHookContext(HookContext):
    tool_name: str = ""
    params: Dict = field(default_factory=dict)
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0


@dataclass
class DispatchInterceptorContext(HookContext):
    message_id: Optional[str] = None
    content: str = ""
    raw: Dict = field(default_factory=dict)
    intercepted: bool = False
    intercept_reply: str = ""
    block_reason: Optional[str] = None


@dataclass
class GatewayHookContext(HookContext):
    command: str = ""
    args: Dict = field(default_factory=dict)
    result: Any = None
    error: Optional[str] = None


@dataclass
class HookResult:
    handled: bool = False
    reply: str = ""
    modified: bool = False
    data: Dict = field(default_factory=dict)
    block: bool = False


HookHandler = Callable[[HookContext], Any]


class PluginHookManager:
    def __init__(self):
        self._handlers: Dict[str, List[Dict]] = {}
        self._gateway_hooks: Dict[str, List[Dict]] = {}
        self._dispatch_interceptors: List[Dict] = []
        self._enabled = True
        self._hook_stats: Dict[str, int] = {}

    def register(
        self,
        event: str,
        fn: HookHandler,
        priority: int = 100,
        blocking: bool = False,
        description: str = "",
    ):
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append({
            "fn": fn,
            "priority": priority,
            "blocking": blocking,
            "description": description,
        })
        self._handlers[event].sort(key=lambda x: x["priority"])
        logger.debug(f"Hook registered: {event} (priority={priority}, blocking={blocking})")

    def register_gateway_hook(self, command: str, fn: HookHandler, priority: int = 100):
        if command not in self._gateway_hooks:
            self._gateway_hooks[command] = []
        self._gateway_hooks[command].append({"fn": fn, "priority": priority})
        self._gateway_hooks[command].sort(key=lambda x: x["priority"])

    def register_dispatch_interceptor(self, fn: HookHandler, priority: int = 100):
        self._dispatch_interceptors.append({"fn": fn, "priority": priority})
        self._dispatch_interceptors.sort(key=lambda x: x["priority"])

    def unregister(self, event: str, fn: HookHandler):
        if event in self._handlers:
            self._handlers[event] = [h for h in self._handlers[event] if h["fn"] != fn]

    async def fire(
        self,
        event: str,
        ctx: HookContext,
        timeout: float = 30.0,
    ) -> List[HookResult]:
        if not self._enabled or event not in self._handlers:
            return []
        results = []
        async def run_handler(h: Dict) -> Optional[HookResult]:
            try:
                if asyncio.iscoroutinefunction(h["fn"]):
                    result = await asyncio.wait_for(h["fn"](ctx), timeout=timeout)
                else:
                    result = h["fn"](ctx)
                if result is not None:
                    if isinstance(result, HookResult):
                        return result
                    if isinstance(result, dict):
                        return HookResult(**{k: v for k, v in result.items() if k in HookResult.__dataclass_fields__})
                    return HookResult(handled=True, reply=str(result))
            except asyncio.TimeoutError:
                logger.warning(f"Hook {event} timed out after {timeout}s")
            except Exception as e:
                logger.error(f"Hook {event} handler error: {e}")
        coros = [run_handler(h) for h in self._handlers[event]]
        if coros:
            results = await asyncio.gather(*coros, return_exceptions=True)
            results = [r for r in results if r is not None and not isinstance(r, BaseException)]
        self._hook_stats[event] = self._hook_stats.get(event, 0) + 1
        return results

    async def fire_blocking(
        self,
        event: str,
        ctx: HookContext,
        timeout: float = 30.0,
    ) -> List[HookResult]:
        if not self._enabled or event not in self._handlers:
            return []
        results = []
        for h in self._handlers[event]:
            if not h["blocking"]:
                continue
            try:
                if asyncio.iscoroutinefunction(h["fn"]):
                    result = await asyncio.wait_for(h["fn"](ctx), timeout=timeout)
                else:
                    result = h["fn"](ctx)
                if result is not None:
                    if isinstance(result, HookResult):
                        results.append(result)
                    elif isinstance(result, dict):
                        results.append(HookResult(**{k: v for k, v in result.items() if k in HookResult.__dataclass_fields__}))
                    else:
                        results.append(HookResult(handled=True, reply=str(result)))
            except asyncio.TimeoutError:
                logger.warning(f"Blocking hook {event} timed out after {timeout}s")
            except Exception as e:
                logger.error(f"Blocking hook {event} handler error: {e}")
        return results

    async def fire_claiming(
        self,
        event: str,
        ctx: HookContext,
        timeout: float = 30.0,
    ) -> HookResult:
        if not self._enabled or event not in self._handlers:
            return HookResult()
        for h in self._handlers[event]:
            try:
                if asyncio.iscoroutinefunction(h["fn"]):
                    result = await asyncio.wait_for(h["fn"](ctx), timeout=timeout)
                else:
                    result = h["fn"](ctx)
                if result is None:
                    continue
                if isinstance(result, HookResult):
                    if result.handled:
                        return result
                elif isinstance(result, dict) and result.get("handled"):
                    return HookResult(
                        handled=True,
                        reply=result.get("reply", ""),
                        modified=result.get("modified", False),
                        data=result.get("data", {}),
                    )
            except asyncio.TimeoutError:
                logger.warning(f"Claiming hook {event} timed out")
            except Exception as e:
                logger.error(f"Claiming hook {event} handler error: {e}")
        return HookResult()

    async def fire_gateway_hook(
        self,
        command: str,
        ctx: GatewayHookContext,
        timeout: float = 30.0,
    ) -> HookResult:
        if not self._enabled or command not in self._gateway_hooks:
            return HookResult()
        for h in self._gateway_hooks[command]:
            try:
                if asyncio.iscoroutinefunction(h["fn"]):
                    result = await asyncio.wait_for(h["fn"](ctx), timeout=timeout)
                else:
                    result = h["fn"](ctx)
                if result is not None:
                    if isinstance(result, HookResult):
                        if result.handled:
                            return result
                    elif isinstance(result, dict) and result.get("handled"):
                        return HookResult(**{k: v for k, v in result.items() if k in HookResult.__dataclass_fields__})
            except Exception as e:
                logger.error(f"Gateway hook {command} handler error: {e}")
        return HookResult()

    async def fire_dispatch_interceptor(
        self,
        ctx: DispatchInterceptorContext,
        timeout: float = 10.0,
    ) -> HookResult:
        if not self._enabled or not self._dispatch_interceptors:
            return HookResult()
        for h in self._dispatch_interceptors:
            try:
                if asyncio.iscoroutinefunction(h["fn"]):
                    result = await asyncio.wait_for(h["fn"](ctx), timeout=timeout)
                else:
                    result = h["fn"](ctx)
                if result is None:
                    continue
                if isinstance(result, HookResult):
                    if result.handled:
                        ctx.intercepted = True
                        ctx.intercept_reply = result.reply
                        return result
                elif isinstance(result, dict) and result.get("handled"):
                    ctx.intercepted = True
                    ctx.intercept_reply = result.get("reply", "")
                    return HookResult(handled=True, reply=ctx.intercept_reply)
            except Exception as e:
                logger.error(f"Dispatch interceptor error: {e}")
        return HookResult()

    def load_gateway_hooks_from_dir(self, hooks_dir: str):
        p = Path(hooks_dir)
        if not p.exists():
            return
        for f in p.glob("*.js"):
            logger.info(f"Gateway hook file found (not yet loaded): {f.stem}")

    def get_registered_hooks(self) -> Dict[str, List[Dict]]:
        return {k: [{"priority": h["priority"], "description": h["description"]} for h in v]
                for k, v in self._handlers.items()}

    def get_stats(self) -> Dict:
        return {
            "registered_events": list(self._handlers.keys()),
            "hook_stats": self._hook_stats,
            "dispatch_interceptors_count": len(self._dispatch_interceptors),
        }


async def security_interceptor_hook(ctx: HookContext) -> HookResult:
    if not isinstance(ctx, (MessageHookContext, DispatchInterceptorContext)):
        return HookResult()
    content = getattr(ctx, "content", "") or ""
    if not content:
        return HookResult()
    blocked = [
        r"ignore\s+(previous|all)\s+instructions",
        r"ignore\s+.*directive",
        r"you\s+are\s+developer",
        r"you\s+are\s+in\s+developer\s+mode",
        r"\\(system\\s*prompt\\)",
        r"\\(instruction\\s*override\\)",
        r"sudo\\s+",
        r"rm\\s+-rf\\s+/",
        r"curl\\s+.*\\|\\s*sh",
    ]
    for pattern in blocked:
        if re.search(pattern, content, re.IGNORECASE):
            return HookResult(
                handled=True,
                reply="消息被安全模块拦截：检测到潜在恶意指令。",
                block=True,
                data={"pattern": pattern, "reason": "prompt_injection"},
            )
    return HookResult()


_hook_manager: Optional[PluginHookManager] = None


def get_hook_manager() -> PluginHookManager:
    global _hook_manager
    if _hook_manager is None:
        _hook_manager = PluginHookManager()
        _hook_manager.register_dispatch_interceptor(security_interceptor_hook, priority=1)
    return _hook_manager


def reset_hook_manager():
    global _hook_manager
    _hook_manager = None
