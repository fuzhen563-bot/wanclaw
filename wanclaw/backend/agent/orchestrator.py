"""
Agent调度大脑 V2.0
优化算法：意图分类、任务规划、技能路由、资源分配
"""

import asyncio
import json
import logging
import time
import uuid
import re
from typing import Dict, Any, Optional, List, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
from collections import defaultdict

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """意图类型"""
    CHAT = "chat"
    TASK = "task"
    QUERY = "query"
    SKILL = "skill"
    AUTOMATION = "automation"
    ADMIN = "admin"
    UNKNOWN = "unknown"


@dataclass
class Intent:
    """用户意图"""
    type: IntentType
    confidence: float
    entities: Dict[str, Any] = field(default_factory=dict)
    raw_input: str = ""
    requires_planning: bool = False
    suggested_skills: List[str] = field(default_factory=list)
    priority: int = 5


class TrieNode:
    """前缀树节点 - 用于高效关键词匹配"""
    def __init__(self):
        self.children: Dict[str, TrieNode] = {}
        self.is_end: bool = False
        self.intent_type: Optional[IntentType] = None
        self.confidence: float = 0.0


class TrieMatcher:
    """前缀树匹配器"""
    def __init__(self):
        self.root = TrieNode()
    
    def insert(self, pattern: str, intent_type: IntentType, confidence: float = 0.8):
        node = self.root
        for char in pattern.lower():
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end = True
        node.intent_type = intent_type
        node.confidence = confidence
    
    def search(self, text: str) -> List[Dict]:
        """搜索所有匹配的模式"""
        results = []
        text_lower = text.lower()
        
        # 枚举所有子串进行匹配
        for start in range(len(text_lower)):
            node = self.root
            for end in range(start, len(text_lower)):
                char = text_lower[end]
                if char not in node.children:
                    break
                node = node.children[char]
                if node.is_end:
                    matched_text = text[start:end+1]
                    results.append({
                        "pattern": matched_text,
                        "start": start,
                        "end": end,
                        "intent_type": node.intent_type,
                        "confidence": node.confidence,
                        "length": len(matched_text),  # 用于最长匹配优先
                    })
        
        return results


class IntentClassifier:
    """意图分类器 V2.0 - 使用前缀树优化匹配"""
    
    def __init__(self, llm_client):
        self.llm = llm_client
        self.trie = TrieMatcher()
        self._rules = self._init_rules()
        self._build_trie()
    
    def _init_rules(self) -> List[Dict]:
        """初始化规则（按优先级排序）"""
        return [
            # 高优先级 - 明确动作
            {"patterns": ["执行", "完成", "处理", "生成"], "type": IntentType.TASK, "priority": 10},
            {"patterns": ["自动", "RPA", "点击", "填表", "抓取"], "type": IntentType.AUTOMATION, "priority": 10},
            
            # 中优先级 - 查询类
            {"patterns": ["查询", "搜索", "找", "查看", "看看"], "type": IntentType.QUERY, "priority": 7},
            {"patterns": ["技能", "工具", "功能", "调用"], "type": IntentType.SKILL, "priority": 7},
            
            # 低优先级 - 管理类
            {"patterns": ["管理", "配置", "设置", "修改"], "type": IntentType.ADMIN, "priority": 5},
            
            # 默认 - 闲聊
            {"patterns": ["你好", "嗨", "在吗", "帮助"], "type": IntentType.CHAT, "priority": 3},
        ]
    
    def _build_trie(self):
        """构建前缀树"""
        for rule in self._rules:
            for pattern in rule["patterns"]:
                self.trie.insert(pattern, rule["type"], confidence=rule.get("priority", 5) / 10)
    
    async def classify(self, user_input: str) -> Intent:
        """分类用户意图 - 优化版"""
        # 1. 前缀树快速匹配
        matches = self.trie.search(user_input)
        
        if matches:
            # 选择最长匹配 + 最高优先级
            best_match = max(matches, key=lambda m: (m["length"], m["confidence"]))
            
            return Intent(
                type=best_match["intent_type"],
                confidence=min(0.9, best_match["confidence"]),
                raw_input=user_input,
                requires_planning=best_match["intent_type"] in [IntentType.TASK, IntentType.AUTOMATION],
                priority=10 - len(matches),  # 匹配越多，优先级越高
            )
        
        # 2. LLM分类
        if self.llm:
            try:
                return await self._llm_classify(user_input)
            except Exception as e:
                logger.warning(f"LLM classify failed: {e}")
        
        # 3. 默认
        return Intent(
            type=IntentType.CHAT,
            confidence=0.5,
            raw_input=user_input,
        )
    
    async def _llm_classify(self, user_input: str) -> Intent:
        """LLM辅助分类"""
        messages = [
            {"role": "system", "content": """分析用户输入的意图类型，返回JSON格式：
{"type": "chat|task|query|skill|automaion|admin", "confidence": 0.0-1.0, "entities": {}, "requires_planning": true/false}"""},
            {"role": "user", "content": user_input},
        ]
        
        response = await self.llm.chat(messages)
        text = response.get("text", "")
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                data = json.loads(json_match.group())
                return Intent(
                    type=IntentType(data.get("type", "chat")),
                    confidence=float(data.get("confidence", 0.5)),
                    entities=data.get("entities", {}),
                    raw_input=user_input,
                    requires_planning=data.get("requires_planning", False),
                )
        except Exception as e:
            logger.warning(f"Parse intent failed: {e}")
        
        return Intent(type=IntentType.CHAT, confidence=0.5, raw_input=user_input)


class TaskPlanner:
    """任务规划器 V2.0 - 支持ReAct循环"""
    
    def __init__(self, llm_client):
        self.llm = llm_client
        self.max_steps = 15
        self.execution_history: List[Dict] = []
    
    async def create_plan(self, user_input: str, intent: Intent) -> 'Task':
        """创建执行计划"""
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        
        # 如果意图已经包含步骤，直接使用
        if intent.entities.get("steps"):
            return Task(
                task_id=task_id,
                name=intent.entities.get("name", "任务"),
                description=user_input,
                steps=intent.entities["steps"],
            )
        
        # LLM规划
        if self.llm:
            try:
                return await self._llm_plan(user_input, intent, task_id)
            except Exception as e:
                logger.warning(f"LLM plan failed: {e}")
        
        # 回退：简单计划
        return Task(
            task_id=task_id,
            name="任务",
            description=user_input,
            steps=[{"action": "execute_skill", "input": {}}],
        )
    
    async def create_react_plan(self, user_input: str, available_tools: List[Dict]) -> 'Task':
        """创建ReAct风格的计划"""
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        
        if not self.llm:
            return Task(
                task_id=task_id,
                name="ReAct任务",
                description=user_input,
                steps=[{"action": "execute_skill", "input": {}}],
            )
        
        # 构建提示
        tools_desc = "\n".join([f"- {t['name']}: {t['description']}" for t in available_tools])
        
        prompt = f"""将用户目标分解为ReAct步骤。格式：
{{"Name": "任务名", "steps": [{{"thought": "思考", "action": "工具名", "input": {{"参数"}}, "observation": ""}}]}}

可用工具：
{tools_desc}

目标：{user_input}"""
        
        messages = [
            {"role": "system", "content": "你是一个任务规划助手，使用ReAct模式规划任务。"},
            {"role": "user", "content": prompt},
        ]
        
        try:
            response = await self.llm.chat(messages)
            text = response.get("text", "")
            
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                data = json.loads(json_match.group())
                steps = []
                for step in data.get("steps", []):
                    steps.append({
                        "action": step.get("action", "execute_skill"),
                        "input": step.get("input", {}),
                        "thought": step.get("thought", ""),
                    })
                
                return Task(
                    task_id=task_id,
                    name=data.get("name", "ReAct任务"),
                    description=user_input,
                    steps=steps,
                )
        except Exception as e:
            logger.warning(f"Parse ReAct plan failed: {e}")
        
        return Task(
            task_id=task_id,
            name="ReAct任务",
            description=user_input,
            steps=[{"action": "execute_skill", "input": {}}],
        )
    
    async def _llm_plan(self, user_input: str, intent: Intent, task_id: str) -> 'Task':
        """LLM生成计划"""
        messages = [
            {"role": "system", "content": """将用户目标分解为具体执行步骤。格式：
{"name": "任务名称", "steps": [{"action": "动作", "input": {}, "description": "描述", "requires_result": false}]}"""},
            {"role": "user", "content": user_input},
        ]
        
        response = await self.llm.chat(messages)
        text = response.get("text", "")
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                data = json.loads(json_match.group())
                return Task(
                    task_id=task_id,
                    name=data.get("name", "任务"),
                    description=user_input,
                    steps=data.get("steps", []),
                )
        except Exception as e:
            logger.warning(f"Parse plan failed: {e}")
        
        raise Exception("Plan generation failed")


class SkillRouter:
    """技能路由 V2.0 - 多策略融合"""
    
    def __init__(self, skill_manager):
        self.skill_manager = skill_manager
        self._skill_index: Dict[str, List[str]] = {}
        self._skill_metadata: Dict[str, Dict] = {}  # 技能元数据
        self._user_preferences: Dict[str, Set[str]] = defaultdict(set)  # 用户偏好
    
    async def initialize(self):
        """初始化技能索引"""
        if self.skill_manager:
            skills = await self.skill_manager.list_skills()
            for skill in skills:
                name = skill.get("name", "")
                keywords = skill.get("keywords", [])
                self._skill_metadata[name] = skill
                
                for kw in keywords:
                    if kw not in self._skill_index:
                        self._skill_index[kw] = []
                    self._skill_index[kw].append(name)
    
    async def route(self, intent: Intent, user_id: str = None) -> List[Dict[str, Any]]:
        """路由到技能 - 多策略融合"""
        results = []
        seen = set()
        
        # 策略1: 明确指定技能
        if intent.entities.get("skill_name"):
            skill_name = intent.entities["skill_name"]
            results.append({"skill": skill_name, "confidence": 0.95, "source": "explicit"})
            seen.add(skill_name)
        
        # 策略2: 用户偏好
        if user_id and user_id in self._user_preferences:
            for skill in self._user_preferences[user_id]:
                if skill not in seen:
                    results.append({"skill": skill, "confidence": 0.85, "source": "preference"})
                    seen.add(skill)
        
        # 策略3: 关键词匹配 (TF-IDF风格)
        keyword_scores = self._keyword_scoring(intent.raw_input)
        for skill_name, score in keyword_scores:
            if skill_name not in seen:
                results.append({"skill": skill_name, "confidence": score, "source": "keyword"})
                seen.add(skill_name)
        
        # 策略4: 意图推荐
        for skill_name in intent.suggested_skills:
            if skill_name not in seen:
                results.append({"skill": skill_name, "confidence": 0.8, "source": "intent"})
                seen.add(skill_name)
        
        # 按置信度排序
        return sorted(results, key=lambda x: x["confidence"], reverse=True)[:5]
    
    def _keyword_scoring(self, text: str) -> List[tuple]:
        """关键词评分 (简化TF-IDF)"""
        text_lower = text.lower()
        words = set(re.findall(r'\w+', text_lower))
        
        scores = []
        for keyword, skills in self._skill_index.items():
            if keyword.lower() in text_lower:
                # 词频 * 逆文档频率 (这里简化处理)
                tf = text_lower.count(keyword.lower())
                idf = 1.0 / len(skills)  # 技能越少，idf越高
                score = tf * idf
                
                for skill in skills:
                    scores.append((skill, min(0.9, score)))
        
        # 去重并取最高分
        skill_best_score = {}
        for skill, score in scores:
            if skill not in skill_best_score or skill_best_score[skill] < score:
                skill_best_score[skill] = score
        
        return sorted(skill_best_score.items(), key=lambda x: x[1], reverse=True)
    
    def record_preference(self, user_id: str, skill_name: str):
        """记录用户偏好"""
        self._user_preferences[user_id].add(skill_name)


class ResourceAllocator:
    """资源分配器 V2.0 - 智能调度"""
    
    def __init__(self):
        self._allocations: Dict[str, 'ResourceAllocation'] = {}
        self._limits = {
            "max_concurrent_tasks": 10,
            "max_cpu_cores": 4.0,
            "max_memory_mb": 4096,
        }
        self._queue_priority: Dict[str, int] = {}  # 任务优先级队列
    
    def allocate(self, task: 'Task', priority: int = 5) -> 'ResourceAllocation':
        """分配资源 - 基于优先级和任务类型"""
        # 检查是否可分配
        if len(self._allocations) >= self._limits["max_concurrent_tasks"]:
            # 尝试抢占最低优先级资源
            lowest_priority_task = min(
                self._allocations.items(),
                key=lambda x: self._queue_priority.get(x[0], 0)
            )
            if priority > self._queue_priority.get(lowest_priority_task[0], 0):
                # 抢占
                del self._allocations[lowest_priority_task[0]]
            else:
                # 排队
                self._queue_priority[task.task_id] = priority
        
        # 基于任务类型分配
        cpu = 0.5 if priority < 5 else 1.0 if priority < 8 else 2.0
        memory = 256 if priority < 5 else 512 if priority < 8 else 1024
        duration = 60 if priority < 5 else 180 if priority < 8 else 600
        
        allocation = ResourceAllocation(
            cpu_cores=cpu,
            memory_mb=memory,
            max_duration=duration,
            priority=priority,
        )
        
        self._allocations[task.task_id] = allocation
        self._queue_priority[task.task_id] = priority
        
        return allocation
    
    def release(self, task_id: str):
        """释放资源"""
        if task_id in self._allocations:
            del self._allocations[task_id]
        if task_id in self._queue_priority:
            del self._queue_priority[task_id]
    
    def get_load_factor(self) -> float:
        """获取负载因子"""
        return len(self._allocations) / self._limits["max_concurrent_tasks"]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取资源统计"""
        total_cpu = sum(a.cpu_cores for a in self._allocations.values())
        total_memory = sum(a.memory_mb for a in self._allocations.values())
        
        return {
            "allocated": len(self._allocations),
            "max_concurrent": self._limits["max_concurrent_tasks"],
            "load_factor": self.get_load_factor(),
            "cpu_cores": {"total": self._limits["max_cpu_cores"], "used": total_cpu},
            "memory_mb": {"total": self._limits["max_memory_mb"], "used": total_memory},
        }


@dataclass
class Task:
    """任务"""
    task_id: str
    name: str
    description: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "pending"
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class ResourceAllocation:
    """资源分配"""
    cpu_cores: float = 1.0
    memory_mb: int = 512
    max_duration: int = 300
    priority: int = 5


class AgentOrchestrator:
    """中央Agent调度器 V2.0"""
    
    def __init__(
        self,
        llm_client=None,
        skill_manager=None,
        memory=None,
        task_queue=None,
    ):
        self.llm = llm_client
        self.skill_manager = skill_manager
        self.memory = memory
        self.task_queue = task_queue
        
        # 初始化组件
        self.intent_classifier = IntentClassifier(llm_client) if llm_client else None
        self.task_planner = TaskPlanner(llm_client) if llm_client else None
        self.skill_router = SkillRouter(skill_manager)
        self.resource_allocator = ResourceAllocator()
        
        # 执行器
        self._executors: Dict[str, Callable] = {}
        
        # 状态
        self._running_tasks: Dict[str, Task] = {}
        self._task_history: List[Task] = []
        
        # 性能指标
        self._metrics = {
            "total_processed": 0,
            "success_count": 0,
            "failure_count": 0,
            "avg_latency_ms": 0,
        }
    
    def register_executor(self, name: str, executor: Callable):
        """注册执行器"""
        self._executors[name] = executor
    
    async def initialize(self):
        """初始化"""
        await self.skill_router.initialize()
        logger.info("AgentOrchestrator V2.0 initialized")
    
    async def process(self, user_input: str, context: Dict = None) -> Dict[str, Any]:
        """处理用户输入 - 优化版"""
        context = context or {}
        session_id = context.get("session_id", "default")
        user_id = context.get("user_id")
        
        start_time = time.time()
        
        # 1. 意图分类
        intent = await self.intent_classifier.classify(user_input) if self.intent_classifier else None
        
        if not intent:
            intent = Intent(type=IntentType.CHAT, confidence=0.5, raw_input=user_input)
        
        logger.info(f"Intent: {intent.type.value}, confidence: {intent.confidence}")
        
        # 2. 技能路由 (并行)
        skills = await self.skill_router.route(intent, user_id)
        
        # 3. 任务规划 (如果需要)
        task = None
        if intent.requires_planning and self.task_planner:
            task = await self.task_planner.create_plan(user_input, intent)
            self.resource_allocator.allocate(task, intent.priority)
        
        # 4. 执行
        result = await self._execute(intent, task, skills, context)
        
        # 5. 记录用户偏好
        if skills and user_id:
            self.skill_router.record_preference(user_id, skills[0]["skill"])
        
        # 6. 清理资源
        if task:
            self.resource_allocator.release(task.task_id)
        
        # 7. 更新指标
        latency_ms = (time.time() - start_time) * 1000
        self._update_metrics(result.get("success", False), latency_ms)
        
        return {
            "intent": {
                "type": intent.type.value,
                "confidence": intent.confidence,
            },
            "task_id": task.task_id if task else None,
            "skills_used": [s["skill"] for s in skills],
            "result": result,
            "success": result.get("success", False),
            "latency_ms": round(latency_ms, 2),
        }
    
    def _update_metrics(self, success: bool, latency_ms: float):
        """更新性能指标"""
        self._metrics["total_processed"] += 1
        if success:
            self._metrics["success_count"] += 1
        else:
            self._metrics["failure_count"] += 1
        
        # 滑动平均
        n = self._metrics["total_processed"]
        old_avg = self._metrics["avg_latency_ms"]
        self._metrics["avg_latency_ms"] = (old_avg * (n - 1) + latency_ms) / n
    
    async def _execute(
        self,
        intent: Intent,
        task: Optional[Task],
        skills: List[Dict],
        context: Dict,
    ) -> Dict[str, Any]:
        """执行任务"""
        if task:
            return await self._execute_task(task, context)
        
        if skills:
            skill_name = skills[0]["skill"]
            return await self._execute_skill(skill_name, context)
        
        if self.llm:
            messages = [
                {"role": "system", "content": "你是一个友好的AI助手"},
                {"role": "user", "content": intent.raw_input},
            ]
            response = await self.llm.chat(messages)
            return {"success": True, "response": response.get("text", "")}
        
        return {"success": False, "error": "No handler available"}
    
    async def _execute_task(self, task: Task, context: Dict) -> Dict[str, Any]:
        """执行任务"""
        task.status = "running"
        task.started_at = datetime.now()
        self._running_tasks[task.task_id] = task
        
        results = []
        
        for i, step in enumerate(task.steps):
            action = step.get("action")
            step_input = step.get("input", {})
            
            # 处理依赖
            if step.get("requires_result") and results:
                step_input["_previous_result"] = results[-1]
            
            try:
                executor = self._executors.get(action)
                if executor:
                    if asyncio.iscoroutinefunction(executor):
                        result = await executor(step_input)
                    else:
                        result = executor(step_input)
                    results.append(result)
                else:
                    results.append({"error": f"No executor for: {action}"})
                    
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                return {"success": False, "error": str(e), "results": results}
        
        task.status = "completed"
        task.completed_at = datetime.now()
        task.result = results
        self._task_history.append(task)
        
        if task.task_id in self._running_tasks:
            del self._running_tasks[task.task_id]
        
        return {"success": True, "results": results}
    
    async def _execute_skill(self, skill_name: str, context: Dict) -> Dict[str, Any]:
        """执行技能"""
        if self.skill_manager:
            try:
                result = await self.skill_manager.execute(skill_name, context)
                return {"success": True, "result": result}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "Skill manager not available"}
    
    async def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        task = self._running_tasks.get(task_id)
        if task:
            return {
                "task_id": task.task_id,
                "status": task.status,
                "started_at": task.started_at.isoformat() if task.started_at else None,
            }
        
        for t in self._task_history:
            if t.task_id == task_id:
                return {
                    "task_id": t.task_id,
                    "status": t.status,
                    "result": t.result,
                    "error": t.error,
                }
        
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        return {
            "running_tasks": len(self._running_tasks),
            "total_tasks": len(self._task_history),
            "resource_allocation": self.resource_allocator.get_stats(),
            "metrics": self._metrics,
        }


# 全局实例
_orchestrator: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    """获取调度器单例"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator