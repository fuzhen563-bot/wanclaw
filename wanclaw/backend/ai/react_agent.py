"""
ReAct Agent - 基于LangChain的工具链规划Agent
支持多步骤自主任务分解、链式执行、反思机制
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class AgentActionType(Enum):
    CALL_TOOL = "call_tool"
    FINAL_ANSWER = "final_answer"
    OBSERVATION = "observation"


@dataclass
class AgentThought:
    """思考步骤"""
    step: int
    thought: str
    action: Optional[str] = None
    action_input: Optional[Dict] = None
    observation: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class ExecutionPlan:
    """执行计划"""
    plan_id: str
    goal: str
    steps: List[Dict[str, Any]]
    current_step: int = 0
    status: str = "pending"
    result: Any = None
    created_at: datetime = field(default_factory=datetime.now)


class BaseTool(ABC):
    """工具基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """返回LangChain工具格式"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            }
        }


class SkillTool(BaseTool):
    """技能执行工具"""
    
    def __init__(self, skill_manager):
        self.skill_manager = skill_manager
    
    @property
    def name(self) -> str:
        return "execute_skill"
    
    @property
    def description(self) -> str:
        return "执行指定技能完成任务，如文件处理、数据分析、自动化操作等。输入技能名称和参数。"
    
    async def execute(self, skill_name: str, parameters: Dict[str, Any] = None, **kwargs) -> str:
        """执行技能"""
        try:
            result = await self.skill_manager.execute(skill_name, parameters or kwargs)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string", "description": "技能名称"},
                    "parameters": {"type": "object", "description": "技能参数"},
                },
                "required": ["skill_name"],
            }
        }


class SearchTool(BaseTool):
    """搜索工具"""
    
    def __init__(self, search_function: Callable = None):
        self.search_func = search_function
    
    @property
    def name(self) -> str:
        return "search"
    
    @property
    def description(self) -> str:
        return "搜索互联网获取信息。用于查询最新数据、验证事实等。"
    
    async def execute(self, query: str, **kwargs) -> str:
        """执行搜索"""
        if self.search_func:
            result = await self.search_func(query)
            return json.dumps(result, ensure_ascii=False)
        return json.dumps({"error": "Search function not configured"})
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                },
                "required": ["query"],
            }
        }


class CalculatorTool(BaseTool):
    """计算工具"""
    
    @property
    def name(self) -> str:
        return "calculator"
    
    @property
    def description(self) -> str:
        return "执行数学计算。用于数据分析、数值处理等。"
    
    async def execute(self, expression: str, **kwargs) -> str:
        """执行计算"""
        try:
            import ast
            import operator
            
            # 安全计算
            allowed_ops = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.Pow: operator.pow,
                ast.USub: operator.neg,
            }
            
            def eval_node(node):
                if isinstance(node, ast.Constant):
                    return node.value
                elif isinstance(node, ast.BinOp):
                    left = eval_node(node.left)
                    right = eval_node(node.right)
                    return allowed_ops[type(node.op)](left, right)
                elif isinstance(node, ast.UnaryOp):
                    return allowed_ops[type(node.op)](eval_node(node.operand))
            
            tree = ast.parse(expression, mode='eval')
            result = eval_node(tree.body)
            return json.dumps({"result": result, "expression": expression})
        except Exception as e:
            return json.dumps({"error": str(e), "expression": expression})
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "数学表达式"},
                },
                "required": ["expression"],
            }
        }


class FileOperationTool(BaseTool):
    """文件操作工具"""
    
    def __init__(self, base_dir: str = "/tmp/wanclaw"):
        self.base_dir = base_dir
        import os
        os.makedirs(base_dir, exist_ok=True)
    
    @property
    def name(self) -> str:
        return "file_operation"
    
    @property
    def description(self) -> str:
        return "文件操作：读取、写入、列表、删除文件。"
    
    async def execute(self, operation: str, path: str = None, content: str = None, **kwargs) -> str:
        """执行文件操作"""
        import os
        import aiofiles
        
        full_path = os.path.join(self.base_dir, path) if path else None
        
        try:
            if operation == "read":
                if full_path and os.path.exists(full_path):
                    async with aiofiles.open(full_path, 'r') as f:
                        return await f.read()
                return ""
            
            elif operation == "write":
                if full_path:
                    async with aiofiles.open(full_path, 'w') as f:
                        await f.write(content or "")
                    return json.dumps({"success": True, "path": path})
                return json.dumps({"error": "path required"})
            
            elif operation == "list":
                if self.base_dir and os.path.exists(self.base_dir):
                    files = os.listdir(self.base_dir)
                    return json.dumps({"files": files})
                return json.dumps({"files": []})
            
            elif operation == "delete":
                if full_path and os.path.exists(full_path):
                    os.remove(full_path)
                    return json.dumps({"success": True})
                return json.dumps({"error": "file not found"})
            
            return json.dumps({"error": f"unknown operation: {operation}"})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["read", "write", "list", "delete"]},
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["operation"],
            }
        }


class MemoryTool(BaseTool):
    """记忆工具"""
    
    def __init__(self, memory_manager):
        self.memory = memory_manager
    
    @property
    def name(self) -> str:
        return "memory"
    
    @property
    def description(self) -> str:
        return "记忆存取：存储或检索重要信息。"
    
    async def execute(self, operation: str, content: str = None, query: str = None, **kwargs) -> str:
        """执行记忆操作"""
        try:
            if operation == "store" or operation == "remember":
                category = kwargs.get("category", "general")
                self.memory.remember(content, category)
                return json.dumps({"success": True, "operation": "stored"})
            
            elif operation == "recall" or operation == "search":
                results = self.memory.recall(query or content)
                return json.dumps({"results": results[:5], "total": len(results)})
            
            return json.dumps({"error": f"unknown operation: {operation}"})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["store", "recall"]},
                    "content": {"type": "string", "description": "要存储的内容"},
                    "query": {"type": "string", "description": "搜索关键词"},
                    "category": {"type": "string", "description": "分类"},
                },
                "required": ["operation"],
            }
        }


class RPATool(BaseTool):
    """RPA操作工具"""
    
    def __init__(self, rpa_manager):
        self.rpa = rpa_manager
    
    @property
    def name(self) -> str:
        return "rpa_execute"
    
    @property
    def description(self) -> str:
        return "RPA自动化：执行浏览器自动化、桌面操作等。"
    
    async def execute(self, action: str, target: str = None, params: Dict = None, **kwargs) -> str:
        """执行RPA操作"""
        try:
            if not self.rpa:
                return json.dumps({"error": "RPA not available"})
            
            result = await self.rpa.execute(action, target, params or kwargs)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "description": "操作类型"},
                    "target": {"type": "string", "description": "目标元素"},
                    "params": {"type": "object", "description": "参数"},
                },
                "required": ["action"],
            }
        }


class ReActAgent:
    """ReAct Agent - 思考-行动-观察循环"""
    
    def __init__(
        self,
        llm_client,
        tools: List[BaseTool] = None,
        memory=None,
        max_iterations: int = 15,
        max_time: int = 300,
    ):
        self.llm = llm_client
        self.tools = {t.name: t for t in (tools or [])}
        self.memory = memory
        self.max_iterations = max_iterations
        self.max_time = max_time
        self.thought_history: List[AgentThought] = []
        
        # 构建提示词
        self.prompt_template = self._build_prompt()
    
    def _build_prompt(self) -> str:
        tool_descriptions = []
        for name, tool in self.tools.items():
            schema = tool.get_schema()
            tool_descriptions.append(f"\n{schema['name']}: {schema['description']}")
        
        return f"""你是一个智能助手，可以通过思考和使用工具来完成任务。

你可以使用以下工具：
{chr(10).join(tool_descriptions)}

你必须按照以下格式思考和行动：

Thought: 你应该先思考当前情况，决定下一步做什么
Action: 选择要使用的工具名称
Action Input: 给工具的输入（JSON格式）
Observation: 观察工具执行的结果
...（这个思考/行动/观察循环可以重复多次）
Thought: 我现在知道最终答案了
Final Answer: 给用户的最终回答

注意：
1. 每次Action后必须等待Observation才能进行下一轮思考
2. 如果工具返回错误，尝试使用其他方法
3. 始终用中文回复
4. 只有在确实完成目标后才输出Final Answer

开始任务！
"""
    
    def add_tool(self, tool: BaseTool):
        """添加工具"""
        self.tools[tool.name] = tool
        self.prompt_template = self._build_prompt()
    
    async def run(self, user_input: str, session_id: str = None) -> Dict[str, Any]:
        """执行ReAct循环"""
        self.thought_history = []
        
        # 构建初始消息
        messages = [
            {"role": "system", "content": self.prompt_template},
            {"role": "user", "content": user_input},
        ]
        
        start_time = time.time()
        iteration = 0
        final_answer = None
        
        while iteration < self.max_iterations and (time.time() - start_time) < self.max_time:
            iteration += 1
            
            # 调用LLM
            response = await self.llm.chat(messages)
            response_text = response.get("text", "")
            
            # 解析响应
            parsed = self._parse_response(response_text)
            
            if not parsed:
                continue
            
            thought = AgentThought(
                step=iteration,
                thought=parsed.get("thought", ""),
                action=parsed.get("action"),
                action_input=parsed.get("action_input"),
            )
            
            # 执行Action
            if parsed.get("action") and parsed.get("action") != "final_answer":
                observation = await self._execute_action(
                    parsed["action"],
                    parsed.get("action_input", {})
                )
                thought.observation = observation
                
                # 添加到消息历史
                messages.append({
                    "role": "user",
                    "content": f"Observation: {observation}"
                })
            elif parsed.get("action") == "final_answer":
                final_answer = parsed.get("final_answer", "")
                break
            
            self.thought_history.append(thought)
            
            # 检查是否完成
            if final_answer:
                break
        
        return {
            "response": final_answer or "任务未能完成",
            "iterations": iteration,
            "thoughts": [
                {
                    "step": t.step,
                    "thought": t.thought,
                    "action": t.action,
                    "observation": t.observation,
                }
                for t in self.thought_history
            ],
            "success": final_answer is not None,
        }
    
    def _parse_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析LLM响应"""
        import re
        
        result = {}
        
        # 提取Thought
        thought_match = re.search(r"Thought:\s*(.+?)(?=\nAction:|$)", response, re.DOTALL)
        if thought_match:
            result["thought"] = thought_match.group(1).strip()
        
        # 提取Action
        action_match = re.search(r"Action:\s*(\w+)", response)
        if action_match:
            result["action"] = action_match.group(1).strip()
        
        # 提取Action Input
        input_match = re.search(r"Action Input:\s*(\{[^}]+\})", response, re.DOTALL)
        if input_match:
            try:
                result["action_input"] = json.loads(input_match.group(1))
            except:
                result["action_input"] = {"input": input_match.group(1).strip()}
        
        # 提取Final Answer
        final_match = re.search(r"Final Answer:\s*(.+)", response, re.DOTALL)
        if final_match:
            result["action"] = "final_answer"
            result["final_answer"] = final_match.group(1).strip()
        
        return result if result.get("thought") or result.get("action") else None
    
    async def _execute_action(self, action_name: str, action_input: Dict) -> str:
        """执行工具"""
        # 查找工具
        tool = self.tools.get(action_name)
        
        if not tool:
            return f"错误：未知工具 '{action_name}'"
        
        try:
            # 执行工具
            result = await tool.execute(**action_input)
            return str(result)
        except Exception as e:
            return f"工具执行错误：{str(e)}"
    
    async def create_plan(self, goal: str) -> ExecutionPlan:
        """创建执行计划"""
        # 使用LLM分解任务
        messages = [
            {"role": "system", "content": "你是一个任务规划助手，将用户目标分解为具体步骤。"},
            {"role": "user", "content": f"请将以下目标分解为具体执行步骤：{goal}\n\n请以JSON格式返回，格式如下：\n{{\"steps\": [{{\"tool\": \"工具名\", \"input\": {{}}, \"description\": \"步骤描述\"}}]}}"},
        ]
        
        response = await self.llm.chat(messages)
        
        try:
            # 尝试解析JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', response.get("text", ""))
            if json_match:
                plan_data = json.loads(json_match.group())
                return ExecutionPlan(
                    plan_id=f"plan-{uuid.uuid4().hex[:8]}",
                    goal=goal,
                    steps=plan_data.get("steps", []),
                )
        except:
            pass
        
        # 回退：返回简单计划
        return ExecutionPlan(
            plan_id=f"plan-{uuid.uuid4().hex[:8]}",
            goal=goal,
            steps=[{"description": "执行任务", "tool": "execute_skill", "input": {}}],
        )
    
    async def execute_plan(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """执行计划"""
        results = []
        
        for i, step in enumerate(plan.steps):
            plan.current_step = i
            
            tool_name = step.get("tool")
            tool_input = step.get("input", {})
            
            tool = self.tools.get(tool_name)
            if tool:
                try:
                    result = await tool.execute(**tool_input)
                    results.append({"step": i, "success": True, "result": result})
                except Exception as e:
                    results.append({"step": i, "success": False, "error": str(e)})
                    plan.status = "failed"
                    break
            else:
                results.append({"step": i, "success": False, "error": f"Tool not found: {tool_name}"})
        
        plan.status = "completed"
        plan.result = results
        
        return {
            "plan_id": plan.plan_id,
            "status": plan.status,
            "results": results,
        }


# 便捷函数
def create_react_agent(
    llm_client,
    skill_manager=None,
    memory=None,
    search_func=None,
) -> ReActAgent:
    """创建ReAct Agent"""
    tools = []
    
    if skill_manager:
        tools.append(SkillTool(skill_manager))
    
    if search_func:
        tools.append(SearchTool(search_func))
    
    tools.append(CalculatorTool())
    tools.append(FileOperationTool())
    
    if memory:
        tools.append(MemoryTool(memory))
    
    return ReActAgent(
        llm_client=llm_client,
        tools=tools,
        memory=memory,
    )