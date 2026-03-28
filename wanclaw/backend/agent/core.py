"""
WanClaw Agent Core

Autonomous agent with tool-calling loop, memory integration,
and multi-step task execution. Inspired by OpenClaw's agent architecture.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AgentTurn:
    turn_id: str
    user_input: str
    thoughts: List[str] = field(default_factory=list)
    actions: List[Dict] = field(default_factory=list)
    result: str = ""
    status: str = "pending"
    start_time: float = field(default_factory=time.time)
    end_time: float = 0


@dataclass
class Tool:
    name: str
    description: str
    parameters: Dict
    handler: Callable
    requires_confirm: bool = False


class AgentCore:
    def __init__(self, llm_client=None, memory=None, skill_manager=None, hook_manager=None):
        self.llm = llm_client
        self.memory = memory
        self.skills = skill_manager
        self.hooks = hook_manager
        self.tools: Dict[str, Tool] = {}
        self.system_prompt = self._build_system_prompt()
        self.max_turns = 10
        self.history: List[Dict] = []
        self._running = False
        self._register_default_tools()

    def _build_system_prompt(self) -> str:
        identity = ""
        if self.memory:
            try:
                identity = self.memory.get_identity()
            except Exception:
                pass
        return f"""{identity}

You are WanClaw, an autonomous AI assistant. You can use tools to complete tasks.

Available tools:
{self._format_tools()}

Instructions:
1. Think step by step about what the user wants
2. Use tools when needed to gather information or take action
3. If a tool fails, try an alternative approach
4. Always respond in the user's language
5. Be concise and helpful

When you need to use a tool, respond with:
THOUGHT: <your reasoning>
ACTION: <tool_name>
INPUT: <json_parameters>
"""

    def _format_tools(self) -> str:
        if not self.tools:
            return "No tools available."
        lines = []
        for name, tool in self.tools.items():
            lines.append(f"- {name}: {tool.description}")
        return "\n".join(lines)

    def _register_default_tools(self):
        self.register_tool(Tool(
            name="remember",
            description="Store information in memory for later recall",
            parameters={"content": "string", "category": "string"},
            handler=self._tool_remember,
        ))
        self.register_tool(Tool(
            name="recall",
            description="Search memory for relevant information",
            parameters={"query": "string", "category": "string"},
            handler=self._tool_recall,
        ))
        self.register_tool(Tool(
            name="execute_skill",
            description="Execute a WanClaw skill",
            parameters={"skill_name": "string", "params": "object"},
            handler=self._tool_execute_skill,
        ))

    def register_tool(self, tool: Tool):
        self.tools[tool.name] = tool
        self.system_prompt = self._build_system_prompt()
        logger.info(f"Tool registered: {tool.name}")

    async def _tool_remember(self, params: Dict) -> str:
        if self.memory:
            self.memory.remember(
                content=params.get("content", ""),
                category=params.get("category", "knowledge"),
                source="agent"
            )
            return "Information stored in memory."
        return "Memory system not available."

    async def _tool_recall(self, params: Dict) -> str:
        if self.memory:
            results = self.memory.recall(
                query=params.get("query", ""),
                category=params.get("category"),
            )
            return json.dumps(results, ensure_ascii=False, indent=2) if results else "No relevant memories found."
        return "Memory system not available."

    async def _tool_execute_skill(self, params: Dict) -> str:
        if self.skills:
            try:
                result = await self.skills.execute_skill(
                    params.get("skill_name", ""),
                    params.get("params", {})
                )
                return json.dumps({
                    "success": result.success,
                    "message": result.message,
                    "data": result.data,
                }, ensure_ascii=False, indent=2)
            except Exception as e:
                return f"Skill execution failed: {e}"
        return "Skill manager not available."

    async def think(self, user_input: str, context: str = "") -> AgentTurn:
        turn = AgentTurn(turn_id=str(uuid.uuid4())[:8], user_input=user_input)
        turn.status = "thinking"

        if self.hooks:
            from wanclaw.backend.agent.hooks import AgentHookContext, LLMCallHookContext, ToolCallHookContext
            agent_ctx = AgentHookContext(user_input=user_input, turn_id=turn.turn_id)
            await self.hooks.fire("before_agent_start", agent_ctx)

        memories = ""
        if self.memory:
            try:
                recalled = self.memory.recall(user_input, limit=3)
                if recalled:
                    memories = "\n".join([f"- {r.get('content', '')}" for r in recalled])
            except Exception:
                pass

        prompt = f"""User request: {user_input}
{f"Context: {context}" if context else ""}
{f"Relevant memories:" + chr(10) + memories if memories else ""}

Think about what the user needs and what tools to use. Respond with THOUGHT/ACTION/INPUT or a direct answer."""

        if not self.llm:
            turn.result = "AI engine not available. Please configure a model provider."
            turn.status = "completed"
            turn.end_time = time.time()
            return turn

        try:
            self.history.append({"role": "user", "content": user_input})
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(self.history[-20:])

            if self.hooks:
                llm_ctx = LLMCallHookContext(
                    messages=messages,
                    system_prompt=self.system_prompt,
                    model=getattr(self.llm, "model", ""),
                )
                await self.hooks.fire_blocking("before_llm_call", llm_ctx)

            response = await self.llm.chat(messages)
            text = response.get("text", "")
            turn.thoughts.append(text)

            if self.hooks:
                llm_ctx.response = response
                await self.hooks.fire("after_llm_call", llm_ctx)

            if "ACTION:" in text and "INPUT:" in text:
                action_line = text.split("ACTION:")[1].split("\n")[0].strip()
                input_line = text.split("INPUT:")[1].strip()
                try:
                    action_params = json.loads(input_line)
                except json.JSONDecodeError:
                    action_params = {"raw": input_line}

                tool = self.tools.get(action_line)
                if tool:
                    turn.actions.append({"tool": action_line, "params": action_params})
                    if self.hooks:
                        tool_ctx = ToolCallHookContext(tool_name=action_line, params=action_params)
                        await self.hooks.fire_blocking("before_tool_call", tool_ctx)
                    start = time.time()
                    result = await tool.handler(action_params)
                    turn.result = result
                    if self.hooks:
                        tool_ctx.result = result
                        tool_ctx.duration_ms = (time.time() - start) * 1000
                        await self.hooks.fire("after_tool_call", tool_ctx)
                else:
                    turn.result = f"Unknown tool: {action_line}"
            else:
                turn.result = text

            self.history.append({"role": "assistant", "content": turn.result})

            if self.memory:
                try:
                    self.memory.log_conversation("agent", "core", "user", user_input)
                    self.memory.log_conversation("agent", "core", "assistant", turn.result)
                except Exception:
                    pass

        except Exception as e:
            turn.result = f"Agent error: {e}"
            logger.error(f"Agent think failed: {e}")

        turn.status = "completed"
        turn.end_time = time.time()

        if self.hooks:
            agent_ctx.result = turn.result
            agent_ctx.status = turn.status
            agent_ctx.thoughts = turn.thoughts
            agent_ctx.actions = turn.actions
            asyncio.create_task(self.hooks.fire("agent_end", agent_ctx))

        return turn

    async def execute_plan(self, steps: List[Dict]) -> List[Dict]:
        results = []
        for step in steps:
            tool_name = step.get("tool", "")
            params = step.get("params", {})
            tool = self.tools.get(tool_name)
            if tool:
                try:
                    result = await tool.handler(params)
                    results.append({"tool": tool_name, "success": True, "result": result})
                except Exception as e:
                    results.append({"tool": tool_name, "success": False, "error": str(e)})
            else:
                results.append({"tool": tool_name, "success": False, "error": f"Unknown tool: {tool_name}"})
        return results

    def get_status(self) -> Dict:
        return {
            "running": self._running,
            "tools": list(self.tools.keys()),
            "history_length": len(self.history),
            "llm_available": self.llm is not None,
            "memory_available": self.memory is not None,
            "skills_available": self.skills is not None,
        }


_agent_core: Optional[AgentCore] = None


def get_agent_core(**kwargs) -> AgentCore:
    global _agent_core
    if _agent_core is None:
        defaults = {}
        if "hook_manager" not in kwargs:
            try:
                from wanclaw.backend.agent import get_hook_manager
                defaults["hook_manager"] = get_hook_manager()
            except Exception:
                pass
        defaults.update(kwargs)
        _agent_core = AgentCore(**defaults)
    return _agent_core
