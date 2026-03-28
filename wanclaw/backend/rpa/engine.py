"""
WanClaw RPA Engine - 自动化执行引擎
AI任务规划 → 标准化执行指令，管控操作全生命周期
支持错误重试、异常兜底、执行日志全链路审计
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .playwright_driver import BrowserType, RPAManager

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class ActionType(Enum):
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    WAIT = "wait"
    SCREENSHOT = "screenshot"
    EXTRACT = "extract"
    HOVER = "hover"
    SELECT = "select"
    EVALUATE = "evaluate"
    SWITCH_FRAME = "switch_frame"
    SWITCH_TAB = "switch_tab"
    SCROLL = "scroll"
    DRAG = "drag"
    KEYBOARD = "keyboard"
    CUSTOM = "custom"


@dataclass
class ExecutionContext:
    execution_id: str
    task_id: str
    tenant_id: str
    status: ExecutionStatus
    current_action: int = 0
    total_actions: int = 0
    actions: List[Dict] = field(default_factory=list)
    results: List[Dict] = field(default_factory=list)
    errors: List[Dict] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    success: bool
    action_index: int
    action_type: str
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    snapshot: Optional[Dict] = None


@dataclass
class ExecutionPlan:
    steps: List[Dict[str, Any]]
    estimated_duration: float = 0.0
    risk_level: str = "low"
    requires_confirmation: List[int] = field(default_factory=list)


class RPALogger:
    def __init__(self, execution_id: str):
        self.execution_id = execution_id
        self.entries: List[Dict] = []

    def log(self, level: str, action: str, details: Dict[str, Any] = None):
        entry = {
            "execution_id": self.execution_id,
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "action": action,
            "details": details or {},
        }
        self.entries.append(entry)
        getattr(logger, level)(f"[RPA:{self.execution_id[:8]}] {action}", extra=details)

    def get_full_log(self) -> str:
        return json.dumps(self.entries, ensure_ascii=False, indent=2)


class RPAEngine:
    def __init__(self, tenant_id: str = "default"):
        self.tenant_id = tenant_id
        self._rpa_manager = RPAManager()
        self._executors: Dict[str, Callable] = {}
        self._running_contexts: Dict[str, ExecutionContext] = {}
        self._register_default_executors()
        self._safety_whitelist: List[str] = []
        self._safety_blacklist: List[str] = []

    def _register_default_executors(self):
        self._executors[ActionType.NAVIGATE.value] = self._execute_navigate
        self._executors[ActionType.CLICK.value] = self._execute_click
        self._executors[ActionType.TYPE.value] = self._execute_type
        self._executors[ActionType.WAIT.value] = self._execute_wait
        self._executors[ActionType.SCREENSHOT.value] = self._execute_screenshot
        self._executors[ActionType.EXTRACT.value] = self._execute_extract
        self._executors[ActionType.HOVER.value] = self._execute_hover
        self._executors[ActionType.SELECT.value] = self._execute_select
        self._executors[ActionType.EVALUATE.value] = self._execute_evaluate
        self._executors[ActionType.SWITCH_TAB.value] = self._execute_switch_tab
        self._executors[ActionType.SCROLL.value] = self._execute_scroll
        self._executors[ActionType.KEYBOARD.value] = self._execute_keyboard

    def set_safety_rules(self, whitelist: List[str] = None, blacklist: List[str] = None):
        if whitelist:
            self._safety_whitelist = whitelist
        if blacklist:
            self._safety_blacklist = blacklist

    async def create_execution(
        self,
        task_id: str,
        plan: ExecutionPlan,
        max_retries: int = 3,
        metadata: Dict[str, Any] = None,
    ) -> str:
        execution_id = f"exec-{uuid.uuid4().hex[:12]}"
        context = ExecutionContext(
            execution_id=execution_id,
            task_id=task_id,
            tenant_id=self.tenant_id,
            status=ExecutionStatus.PENDING,
            total_actions=len(plan.steps),
            actions=plan.steps,
            max_retries=max_retries,
            metadata=metadata or {},
        )
        self._running_contexts[execution_id] = context
        return execution_id

    async def execute(self, execution_id: str) -> ExecutionContext:
        context = self._running_contexts.get(execution_id)
        if not context:
            raise ValueError(f"Execution {execution_id} not found")

        context.status = ExecutionStatus.RUNNING
        context.started_at = datetime.now()
        logger = RPALogger(execution_id)
        logger.log("info", "execution_started", {"task_id": context.task_id, "total_actions": context.total_actions})

        try:
            for i, action in enumerate(context.actions):
                if context.status == ExecutionStatus.CANCELLED:
                    break

                context.current_action = i
                result = await self._execute_action(action, i, context, logger)

                if result.success:
                    context.results.append({
                        "action_index": i,
                        "type": action.get("type"),
                        "output": result.output,
                        "duration_ms": result.duration_ms,
                    })
                    logger.log("info", "action_completed", {"index": i, "type": action.get("type"), "duration_ms": result.duration_ms})
                else:
                    context.errors.append({
                        "action_index": i,
                        "type": action.get("type"),
                        "error": result.error,
                        "timestamp": datetime.now().isoformat(),
                    })
                    logger.log("error", "action_failed", {"index": i, "type": action.get("type"), "error": result.error})

                    if context.retry_count < context.max_retries:
                        context.retry_count += 1
                        context.status = ExecutionStatus.RETRYING
                        logger.log("warning", "action_retry", {"retry": context.retry_count, "max": context.max_retries})
                        await asyncio.sleep(1 * context.retry_count)
                        context.status = ExecutionStatus.RUNNING
                        result = await self._execute_action(action, i, context, logger)
                        if result.success:
                            context.results.append({
                                "action_index": i,
                                "type": action.get("type"),
                                "output": result.output,
                                "duration_ms": result.duration_ms,
                                "retry": context.retry_count,
                            })
                            continue

                    logger.log("error", "execution_aborted", {"failed_at": i})
                    context.status = ExecutionStatus.FAILED
                    break

        except Exception as e:
            logger.log("error", "execution_error", {"error": str(e)})
            context.status = ExecutionStatus.FAILED
            context.errors.append({"action_index": context.current_action, "error": str(e)})

        context.completed_at = datetime.now()
        context.status = ExecutionStatus.COMPLETED if not context.errors else ExecutionStatus.FAILED
        logger.log("info", "execution_completed", {"status": context.status.value, "completed_actions": len(context.results), "failed_actions": len(context.errors)})

        return context

    async def _execute_action(self, action: Dict, index: int, context: ExecutionContext, logger: RPALogger) -> ExecutionResult:
        action_type = action.get("type", ActionType.CUSTOM.value)
        start_time = asyncio.get_event_loop().time()

        if action_type in self._safety_blacklist:
            return ExecutionResult(False, index, action_type, error=f"Action {action_type} is blacklisted", duration_ms=0)

        if self._safety_whitelist and action_type not in self._safety_whitelist:
            return ExecutionResult(False, index, action_type, error=f"Action {action_type} not in whitelist", duration_ms=0)

        if action.get("requires_confirmation"):
            logger.log("warning", "action_requires_confirmation", {"index": index, "type": action_type})
            return ExecutionResult(False, index, action_type, error="Action requires manual confirmation", duration_ms=0)

        executor = self._executors.get(action_type)
        if not executor:
            return ExecutionResult(False, index, action_type, error=f"No executor for {action_type}", duration_ms=0)

        try:
            output = await executor(action, context)
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            return ExecutionResult(True, index, action_type, output=output, duration_ms=duration_ms)
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            return ExecutionResult(False, index, action_type, error=str(e), duration_ms=duration_ms)

    async def _execute_navigate(self, action: Dict, context: ExecutionContext) -> Any:
        url = action.get("value")
        await self._rpa_manager.execute("goto", url)
        return {"url": url}

    async def _execute_click(self, action: Dict, context: ExecutionContext) -> Any:
        selector = action.get("selector", {})
        await self._rpa_manager.execute("click", selector)
        return {"clicked": selector}

    async def _execute_type(self, action: Dict, context: ExecutionContext) -> Any:
        selector = action.get("selector", {})
        text = action.get("value", "")
        await self._rpa_manager.execute("type", selector, text)
        return {"typed": text, "selector": selector}

    async def _execute_wait(self, action: Dict, context: ExecutionContext) -> Any:
        wait_type = action.get("params", {}).get("type", "selector")
        value = action.get("params", {}).get("value", "")
        duration = float(action.get("params", {}).get("duration", 1000)) / 1000
        await asyncio.sleep(duration)
        return {"waited": duration, "type": wait_type, "value": value}

    async def _execute_screenshot(self, action: Dict, context: ExecutionContext) -> Any:
        result = await self._rpa_manager.execute("screenshot", action.get("params", {}).get("url", ""))
        return {"screenshot": result}

    async def _execute_extract(self, action: Dict, context: ExecutionContext) -> Any:
        selector = action.get("selector", {})
        result = await self._rpa_manager.execute("extract", selector)
        return {"extracted": result}

    async def _execute_hover(self, action: Dict, context: ExecutionContext) -> Any:
        selector = action.get("selector", {})
        await self._rpa_manager.execute("hover", selector)
        return {"hovered": selector}

    async def _execute_select(self, action: Dict, context: ExecutionContext) -> Any:
        selector = action.get("selector", {})
        value = action.get("value", "")
        await self._rpa_manager.execute("select", selector, value)
        return {"selected": value, "selector": selector}

    async def _execute_evaluate(self, action: Dict, context: ExecutionContext) -> Any:
        script = action.get("value", "")
        result = await self._rpa_manager.execute("evaluate", script)
        return {"result": result}

    async def _execute_switch_tab(self, action: Dict, context: ExecutionContext) -> Any:
        tab_index = action.get("value", 0)
        await self._rpa_manager.execute("switch_tab", tab_index)
        return {"switched_to_tab": tab_index}

    async def _execute_scroll(self, action: Dict, context: ExecutionContext) -> Any:
        x = action.get("params", {}).get("x", 0)
        y = action.get("params", {}).get("y", 0)
        await self._rpa_manager.execute("scroll", {"x": x, "y": y})
        return {"scrolled": {"x": x, "y": y}}

    async def _execute_keyboard(self, action: Dict, context: ExecutionContext) -> Any:
        key = action.get("value", "")
        await self._rpa_manager.execute("keyboard", key)
        return {"key_pressed": key}

    async def cancel(self, execution_id: str) -> bool:
        context = self._running_contexts.get(execution_id)
        if not context:
            return False
        context.status = ExecutionStatus.CANCELLED
        return True

    def get_execution(self, execution_id: str) -> Optional[ExecutionContext]:
        return self._running_contexts.get(execution_id)

    def register_executor(self, action_type: str, executor: Callable):
        self._executors[action_type] = executor


_rpa_engine_instances: Dict[str, RPAEngine] = {}


def get_rpa_engine(tenant_id: str = "default") -> RPAEngine:
    if tenant_id not in _rpa_engine_instances:
        _rpa_engine_instances[tenant_id] = RPAEngine(tenant_id)
    return _rpa_engine_instances[tenant_id]
