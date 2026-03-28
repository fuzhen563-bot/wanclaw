"""
WanClaw Lobster Agentic Loop - 智能调度循环
基于ReAct框架的执行闭环：思考→任务拆解→工具调用→执行→结果校验→迭代优化
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .engine import RPAEngine, ExecutionPlan, ExecutionStatus, get_rpa_engine

logger = logging.getLogger(__name__)


class LoopPhase(Enum):
    THINK = "think"
    PLAN = "plan"
    ACTION = "action"
    OBSERVE = "observe"
    VALIDATE = "validate"
    ITERATE = "iterate"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class Thought:
    phase: LoopPhase
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    reasoning: str = ""


@dataclass
class ActionResult:
    action: Dict[str, Any]
    success: bool
    output: Any = None
    error: Optional[str] = None
    observation: str = ""


@dataclass
class ValidationResult:
    passed: bool
    expected: Any
    actual: Any
    message: str = ""


@dataclass
class LoopContext:
    task_id: str
    tenant_id: str
    original_goal: str
    current_goal: str
    thoughts: List[Thought] = field(default_factory=list)
    actions: List[ActionResult] = field(default_factory=list)
    validation_results: List[ValidationResult] = field(default_factory=list)
    iterations: int = 0
    max_iterations: int = 10
    status: str = "running"
    execution_id: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._descriptions: Dict[str, str] = {}

    def register(self, name: str, func: Callable, description: str = ""):
        self._tools[name] = func
        self._descriptions[name] = description

    def get_tool(self, name: str) -> Optional[Callable]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, str]]:
        return [{"name": name, "description": self._descriptions.get(name, "")} for name in self._tools]

    def get_schema(self) -> str:
        schemas = []
        for name, desc in self._descriptions.items():
            schemas.append(f"- {name}: {desc}")
        return "\n".join(schemas)


class LobsterAgent:
    def __init__(self, tenant_id: str = "default"):
        self.tenant_id = tenant_id
        self._rpa_engine = get_rpa_engine(tenant_id)
        self._tool_registry = ToolRegistry()
        self._ai_client = None
        self._contexts: Dict[str, LoopContext] = {}
        self._register_default_tools()

    def _register_default_tools(self):
        self._tool_registry.register("browser_navigate", self._tool_navigate, "导航到指定URL")
        self._tool_registry.register("browser_click", self._tool_click, "点击页面元素")
        self._tool_registry.register("browser_type", self._tool_type, "在输入框中输入文本")
        self._tool_registry.register("browser_screenshot", self._tool_screenshot, "截取当前页面截图")
        self._tool_registry.register("browser_wait", self._tool_wait, "等待指定时间或条件")
        self._tool_registry.register("browser_extract", self._tool_extract, "提取页面文本或数据")
        self._tool_registry.register("browser_scroll", self._tool_scroll, "滚动页面")
        self._tool_registry.register("browser_switch_tab", self._tool_switch_tab, "切换浏览器标签页")
        self._tool_registry.register("validate_content", self._tool_validate, "校验页面内容是否符合预期")

    async def _tool_navigate(self, url: str, context: LoopContext) -> str:
        plan = ExecutionPlan(steps=[{"type": "navigate", "value": url}])
        exec_id = await self._rpa_engine.create_execution(context.task_id, plan)
        exec_ctx = await self._rpa_engine.execute(exec_id)
        return f"已导航到 {url}"

    async def _tool_click(self, selector: str, context: LoopContext) -> str:
        plan = ExecutionPlan(steps=[{"type": "click", "selector": selector}])
        exec_id = await self._rpa_engine.create_execution(context.task_id, plan)
        await self._rpa_engine.execute(exec_id)
        return f"已点击元素 {selector}"

    async def _tool_type(self, selector: str, text: str, context: LoopContext) -> str:
        plan = ExecutionPlan(steps=[{"type": "type", "selector": selector, "value": text}])
        exec_id = await self._rpa_engine.create_execution(context.task_id, plan)
        await self._rpa_engine.execute(exec_id)
        return f"已在 {selector} 输入文本"

    async def _tool_screenshot(self, params: Dict, context: LoopContext) -> str:
        plan = ExecutionPlan(steps=[{"type": "screenshot", "params": params}])
        exec_id = await self._rpa_engine.create_execution(context.task_id, plan)
        await self._rpa_engine.execute(exec_id)
        return "已截取页面"

    async def _tool_wait(self, duration: float, context: LoopContext) -> str:
        plan = ExecutionPlan(steps=[{"type": "wait", "params": {"duration": duration * 1000}}])
        exec_id = await self._rpa_engine.create_execution(context.task_id, plan)
        await self._rpa_engine.execute(exec_id)
        return f"已等待 {duration} 秒"

    async def _tool_extract(self, selector: str, context: LoopContext) -> str:
        plan = ExecutionPlan(steps=[{"type": "extract", "selector": selector}])
        exec_id = await self._rpa_engine.create_execution(context.task_id, plan)
        await self._rpa_engine.execute(exec_id)
        return f"已提取 {selector} 内容"

    async def _tool_scroll(self, x: int, y: int, context: LoopContext) -> str:
        plan = ExecutionPlan(steps=[{"type": "scroll", "params": {"x": x, "y": y}}])
        exec_id = await self._rpa_engine.create_execution(context.task_id, plan)
        await self._rpa_engine.execute(exec_id)
        return f"已滚动到 ({x}, {y})"

    async def _tool_switch_tab(self, tab_index: int, context: LoopContext) -> str:
        plan = ExecutionPlan(steps=[{"type": "switch_tab", "value": tab_index}])
        exec_id = await self._rpa_engine.create_execution(context.task_id, plan)
        await self._rpa_engine.execute(exec_id)
        return f"已切换到标签页 {tab_index}"

    async def _tool_validate(self, expected: str, context: LoopContext, selector: str = None) -> str:
        return f"验证内容: {expected}"

    def set_ai_client(self, client):
        self._ai_client = client

    async def think(self, goal: str, context: LoopContext) -> str:
        context.thoughts.append(Thought(phase=LoopPhase.THINK, content=f"分析目标: {goal}"))
        prompt = f"""你是一个RPA执行规划助手。用户目标: {goal}

可用工具:
{self._tool_registry.get_schema()}

请分析完成这个目标需要哪些步骤，用JSON格式返回:
{{
  "plan": ["步骤1描述", "步骤2描述", ...],
  "estimated_steps": 3,
  "risk_level": "low/medium/high"
}}"""
        if self._ai_client:
            try:
                response = await self._ai_client.chat(prompt)
                return response
            except Exception as e:
                logger.error(f"AI think failed: {e}")
        return json.dumps({"plan": [f"导航到目标页面", "执行操作", "验证结果"], "estimated_steps": 3, "risk_level": "low"})

    async def plan(self, goal: str, ai_response: str, context: LoopContext) -> ExecutionPlan:
        context.thoughts.append(Thought(phase=LoopPhase.PLAN, content="将AI规划转换为执行步骤"))
        try:
            if isinstance(ai_response, str):
                plan_data = json.loads(ai_response)
            else:
                plan_data = ai_response
            steps = plan_data.get("plan", [])
            steps_dict = []
            for step_desc in steps:
                step = self._desc_to_step(step_desc)
                if step:
                    steps_dict.append(step)
            risk_level = plan_data.get("risk_level", "low")
            requires_confirmation = [i for i, s in enumerate(steps_dict) if s.get("risk") == "high"]
            return ExecutionPlan(
                steps=steps_dict,
                estimated_duration=len(steps_dict) * 5.0,
                risk_level=risk_level,
                requires_confirmation=requires_confirmation,
            )
        except Exception as e:
            logger.error(f"Plan parsing failed: {e}")
            return ExecutionPlan(steps=[{"type": "navigate", "value": goal}])

    def _desc_to_step(self, desc: str) -> Optional[Dict]:
        desc_lower = desc.lower()
        if "导航" in desc or "打开" in desc or "访问" in desc:
            url = desc.split("到")[-1].strip() if "到" in desc else ""
            return {"type": "navigate", "value": url}
        elif "点击" in desc:
            return {"type": "click", "selector": {"type": "text", "value": desc}}
        elif "输入" in desc or "填写" in desc:
            return {"type": "type", "value": desc.split("输入")[-1].strip() if "输入" in desc else ""}
        elif "等待" in desc:
            return {"type": "wait", "params": {"duration": 1000}}
        elif "截图" in desc:
            return {"type": "screenshot", "params": {}}
        elif "滚动" in desc:
            return {"type": "scroll", "params": {"x": 0, "y": 300}}
        elif "验证" in desc or "检查" in desc:
            return {"type": "extract", "selector": {}}
        return None

    async def act(self, plan: ExecutionPlan, context: LoopContext) -> List[ActionResult]:
        context.thoughts.append(Thought(phase=LoopPhase.ACTION, content=f"执行 {len(plan.steps)} 个步骤"))
        exec_id = await self._rpa_engine.create_execution(context.task_id, plan)
        context.execution_id = exec_id
        exec_ctx = await self._rpa_engine.execute(exec_id)
        results = []
        for i, result in enumerate(exec_ctx.results):
            action = plan.steps[i] if i < len(plan.steps) else {}
            results.append(ActionResult(
                action=action,
                success=True,
                output=result,
            ))
        for error in exec_ctx.errors:
            action = plan.steps[error["action_index"]] if error["action_index"] < len(plan.steps) else {}
            results.append(ActionResult(
                action=action,
                success=False,
                error=error["error"],
            ))
        context.actions.extend(results)
        return results

    async def observe(self, results: List[ActionResult], context: LoopContext) -> str:
        context.thoughts.append(Thought(phase=LoopPhase.OBSERVE, content="观察执行结果"))
        observations = []
        for i, result in enumerate(results):
            if result.success:
                observations.append(f"步骤{i+1}: 成功 - {result.output}")
            else:
                observations.append(f"步骤{i+1}: 失败 - {result.error}")
        return "\n".join(observations)

    async def validate(self, goal: str, results: List[ActionResult], context: LoopContext) -> ValidationResult:
        context.thoughts.append(Thought(phase=LoopPhase.VALIDATE, content="验证结果是否符合目标"))
        success_count = sum(1 for r in results if r.success)
        total_count = len(results)
        passed = success_count == total_count
        return ValidationResult(
            passed=passed,
            expected=goal,
            actual=f"{success_count}/{total_count} 步骤成功",
            message=f"执行{'成功' if passed else '部分成功'}，{success_count}/{total_count} 步骤完成",
        )

    async def iterate(self, goal: str, validation: ValidationResult, context: LoopContext) -> Optional[str]:
        context.thoughts.append(Thought(phase=LoopPhase.ITERATE, content="根据验证结果调整计划"))
        context.iterations += 1
        if context.iterations >= context.max_iterations:
            context.thoughts.append(Thought(phase=LoopPhase.ERROR, content=f"达到最大迭代次数 {context.max_iterations}"))
            return None
        if validation.passed:
            return None
        failed_actions = [r for r in context.actions if not r.success]
        if failed_actions:
            retry_goal = f"重试: {goal}，上次失败于 {[a.action.get('type') for a in failed_actions]}"
            return retry_goal
        return goal

    async def run(self, task_id: str, goal: str, max_iterations: int = 10) -> LoopContext:
        context = LoopContext(
            task_id=task_id,
            tenant_id=self.tenant_id,
            original_goal=goal,
            current_goal=goal,
            max_iterations=max_iterations,
        )
        self._contexts[task_id] = context
        context.thoughts.append(Thought(phase=LoopPhase.THINK, content=f"开始执行: {goal}"))

        while context.status == "running":
            ai_response = await self.think(context.current_goal, context)
            plan = await self.plan(context.current_goal, ai_response, context)
            results = await self.act(plan, context)
            observation = await self.observe(results, context)
            validation = await self.validate(context.current_goal, results, context)
            context.validation_results.append(validation)

            if validation.passed:
                context.status = "completed"
                context.completed_at = datetime.now()
                context.thoughts.append(Thought(phase=LoopPhase.COMPLETE, content="任务完成"))
                break

            next_goal = await self.iterate(context.current_goal, validation, context)
            if next_goal is None:
                context.status = "failed"
                context.completed_at = datetime.now()
                break

            context.current_goal = next_goal
            context.thoughts.append(Thought(phase=LoopPhase.ITERATE, content=f"调整目标: {next_goal}"))

        return context

    def get_context(self, task_id: str) -> Optional[LoopContext]:
        return self._contexts.get(task_id)

    def register_tool(self, name: str, func: Callable, description: str = ""):
        self._tool_registry.register(name, func, description)


_lobster_instances: Dict[str, LobsterAgent] = {}


def get_lobster_agent(tenant_id: str = "default") -> LobsterAgent:
    if tenant_id not in _lobster_instances:
        _lobster_instances[tenant_id] = LobsterAgent(tenant_id)
    return _lobster_instances[tenant_id]
