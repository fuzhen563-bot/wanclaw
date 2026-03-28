"""
可视化工作流编排引擎 V2.0
优化算法：DAG并行执行、错误恢复、状态管理
"""

import asyncio
import json
import logging
import uuid
import re
import ast
import inspect
from typing import Dict, Any, Optional, List, Callable, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod
from collections import defaultdict, deque

try:
    from croniter import croniter
    CRONITER_AVAILABLE = True
except ImportError:
    CRONITER_AVAILABLE = False

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class NodeType(Enum):
    """节点类型"""
    START = "start"
    END = "end"
    TASK = "task"
    CONDITION = "condition"
    BRANCH = "branch"
    LOOP = "loop"
    PARALLEL = "parallel"
    PARALLEL_BRANCH = "parallel_branch"
    WAIT = "wait"
    HTTP = "http"
    SKILL = "skill"
    SUBWORKFLOW = "subworkflow"
    ERROR = "error"
    RETRY = "retry"


class NodeStatus(Enum):
    """节点状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING = "waiting"
    RETRYING = "retrying"


class TriggerType(Enum):
    """触发类型"""
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EVENT = "event"
    WEBHOOK = "webhook"
    CRON = "cron"


@dataclass
class WorkflowNode:
    """工作流节点"""
    node_id: str
    name: str
    node_type: NodeType
    config: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, int] = field(default_factory=lambda: {"x": 0, "y": 0})
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    retry_config: Dict[str, Any] = field(default_factory=dict)
    timeout: int = 300


@dataclass
class WorkflowEdge:
    """工作流边（连接）"""
    edge_id: str
    source: str
    target: str
    condition: Optional[str] = None
    label: Optional[str] = None
    edge_type: str = "normal"


@dataclass
class Workflow:
    """工作流"""
    workflow_id: str
    name: str
    description: str = ""
    nodes: List[WorkflowNode] = field(default_factory=list)
    edges: List[WorkflowEdge] = field(default_factory=list)
    trigger: TriggerType = TriggerType.MANUAL
    schedule: Optional[str] = None
    enabled: bool = True
    version: int = 1
    max_parallel: int = 5
    error_handling: str = "stop"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_run_at: Optional[datetime] = field(default=None)


@dataclass
class ExecutionContext:
    """执行上下文 V2.0"""
    execution_id: str
    workflow_id: str
    status: NodeStatus = NodeStatus.PENDING
    variables: Dict[str, Any] = field(default_factory=dict)
    node_results: Dict[str, Any] = field(default_factory=dict)
    node_statuses: Dict[str, NodeStatus] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    retry_counts: Dict[str, int] = field(default_factory=dict)
    execution_path: List[str] = field(default_factory=list)
    checkpoint_at: Optional[datetime] = field(default=None)


class DAGExecutor:
    """DAG执行器 V2.0 - 支持并行和错误恢复"""
    
    def __init__(self, workflow: Workflow, executors: Dict[NodeType, 'NodeExecutor']):
        self.workflow = workflow
        self.executors = executors
        self._cycle_nodes: List[str] = []
        self._cycle_path: List[str] = []
        self._build_indexes()
    
    def _build_indexes(self):
        """构建索引以加速查询"""
        # 节点索引
        self._node_map: Dict[str, WorkflowNode] = {n.node_id: n for n in self.workflow.nodes}
        
        # 出边和入边索引
        self._out_edges: Dict[str, List[WorkflowEdge]] = defaultdict(list)
        self._in_edges: Dict[str, List[WorkflowEdge]] = defaultdict(list)
        
        for edge in self.workflow.edges:
            self._out_edges[edge.source].append(edge)
            self._in_edges[edge.target].append(edge)
        
        # 计算入度
        self._in_degree: Dict[str, int] = {n.node_id: len(self._in_edges[n.node_id]) for n in self.workflow.nodes}
        
        # 拓扑排序
        self._topo_order: List[str] = self._topological_sort()
        
        # 计算依赖层级（用于更好的并行分组）
        self._dependency_levels: Dict[str, int] = self._compute_dependency_levels()
    
    def _topological_sort(self) -> List[str]:
        """Kahn算法拓扑排序"""
        in_degree = self._in_degree.copy()
        queue = deque([n for n, d in in_degree.items() if d == 0])
        result = []
        
        while queue:
            node_id = queue.popleft()
            result.append(node_id)
            
            for edge in self._out_edges[node_id]:
                in_degree[edge.target] -= 1
                if in_degree[edge.target] == 0:
                    queue.append(edge.target)
        
        if len(result) != len(self._node_map):
            # Kahn's failed → find the actual cycle nodes via DFS
            self._cycle_path = self._find_cycle_dfs()
            # Unique cycle nodes in order of first appearance in cycle path
            seen = set()
            self._cycle_nodes = []
            for nid in self._cycle_path:
                if nid not in seen:
                    seen.add(nid)
                    self._cycle_nodes.append(nid)
            logger.warning(f"Workflow contains cycles: {self._cycle_nodes}")
        
        return result
    
    def _find_cycle_dfs(self) -> List[str]:
        """DFS-based cycle detection — returns the cycle path."""
        WHITE, GREY, BLACK = 0, 1, 2
        color: Dict[str, int] = {n: WHITE for n in self._node_map}
        parent: Dict[str, Optional[str]] = {n: None for n in self._node_map}
        cycle_path: List[str] = []
        
        def dfs(node_id: str) -> bool:
            color[node_id] = GREY
            for edge in self._out_edges.get(node_id, []):
                target = edge.target
                if target not in self._node_map:
                    continue
                if color[target] == GREY:
                    # Found cycle — reconstruct path
                    cycle_path.append(target)
                    cur = node_id
                    while cur is not None and cur != target:
                        cycle_path.append(cur)
                        cur = parent[cur]
                    cycle_path.reverse()
                    return True
                if color[target] == WHITE:
                    parent[target] = node_id
                    if dfs(target):
                        return True
            color[node_id] = BLACK
            return False
        
        for node_id in self._node_map:
            if color[node_id] == WHITE:
                if dfs(node_id):
                    break
        
        return cycle_path
    
    def _compute_dependency_levels(self) -> Dict[str, int]:
        """Compute topological distance from start nodes (level 0 = start)."""
        levels: Dict[str, int] = {}
        in_degree = self._in_degree.copy()
        queue = deque([n for n, d in in_degree.items() if d == 0])
        
        for n in self._node_map:
            levels[n] = 0 if in_degree[n] == 0 else -1
        
        while queue:
            node_id = queue.popleft()
            current_level = levels[node_id]
            for edge in self._out_edges.get(node_id, []):
                target = edge.target
                new_level = current_level + 1
                if levels[target] < new_level:
                    levels[target] = new_level
                in_degree[target] -= 1
                if in_degree[target] == 0:
                    queue.append(target)
        
        return levels
    
    def get_cycle_info(self) -> Dict[str, Any]:
        """Return cycle diagnostic info."""
        return {
            "has_cycle": len(self._cycle_nodes) > 0,
            "cycle_nodes": self._cycle_nodes,
            "cycle_path": self._cycle_path,
        }
    
    def get_ready_nodes(self, context: ExecutionContext) -> List[str]:
        """获取就绪节点（入度为0且未执行的节点）"""
        ready = []
        
        for node_id in self._topo_order:
            if context.node_statuses.get(node_id) not in [None, NodeStatus.PENDING]:
                continue
            
            # 检查所有前驱节点是否已完成
            predecessors = [e.source for e in self._in_edges[node_id]]
            if all(context.node_statuses.get(p) == NodeStatus.COMPLETED for p in predecessors):
                ready.append(node_id)
        
        return ready
    
    def get_parallel_nodes(self, context: ExecutionContext, max_parallel: int = 5) -> List[str]:
        """获取可并行执行的节点，按依赖层级分组"""
        ready = self.get_ready_nodes(context)
        
        # 按依赖层级分组
        level_groups: Dict[int, List[str]] = defaultdict(list)
        for node_id in ready:
            node = self._node_map[node_id]
            # 只处理可并行化的节点类型
            if node.node_type in [NodeType.TASK, NodeType.SKILL, NodeType.HTTP, NodeType.PARALLEL_BRANCH]:
                level = self._dependency_levels.get(node_id, 0)
                level_groups[level].append(node_id)
        
        if not level_groups:
            return []
        
        # 按层级排序，选择最高优先级的层级
        min_level = min(level_groups.keys())
        level_nodes = level_groups[min_level]
        
        return level_nodes[:max_parallel]


class WorkflowEngine:
    """工作流引擎 V2.0"""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.workflows: Dict[str, Workflow] = {}
        self.execution_contexts: Dict[str, ExecutionContext] = {}
        self._executors: Dict[NodeType, 'NodeExecutor'] = {}
        self._scheduler_task = None
        self._running_executions: Set[str] = set()
        self._event_handlers: Dict[str, Callable] = {}
        self._redis_url = redis_url
        self._redis_client = None
        if redis_url and REDIS_AVAILABLE:
            try:
                import redis as redis_module
                self._redis_client = redis_module.from_url(redis_url, decode_responses=True)
                self._redis_client.ping()
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Persistence disabled.")
                self._redis_client = None
        self._register_default_executors()
    
    def _register_default_executors(self):
        """注册默认执行器"""
        from wanclaw.backend.workflows.engine import (
            TaskExecutor, ConditionExecutor, SkillExecutor,
            HTTPExecutor, WaitExecutor, ParallelExecutor
        )
        
        self._default_executor = DefaultExecutor()
        for node_type in NodeType:
            self._executors[node_type] = self._default_executor
    
    def _build_dag(self, workflow: Workflow) -> Dict[str, List[str]]:
        """从工作流构建DAG邻接表"""
        dag: Dict[str, List[str]] = {node.node_id: [] for node in workflow.nodes}
        
        for edge in workflow.edges:
            if edge.source in dag:
                dag[edge.source].append(edge.target)
        
        return dag
    
    def register_executor(self, node_type: NodeType, executor: 'NodeExecutor'):
        """注册执行器"""
        self._executors[node_type] = executor
    
    async def create_workflow(
        self,
        name: str,
        description: str = "",
        nodes: Optional[List[Dict]] = None,
        edges: Optional[List[Dict]] = None,
        trigger: str = "manual",
        schedule: Optional[str] = None,
        max_parallel: int = 5,
        error_handling: str = "stop",
    ) -> Workflow:
        """创建工作流"""
        workflow_id = f"wf-{uuid.uuid4().hex[:8]}"
        
        workflow = Workflow(
            workflow_id=workflow_id,
            name=name,
            description=description,
            nodes=[WorkflowNode(**n) for n in (nodes or [])],
            edges=[WorkflowEdge(**e) for e in (edges or [])],
            trigger=TriggerType(trigger),
            schedule=schedule,
            max_parallel=max_parallel,
            error_handling=error_handling,
        )
        
        self.workflows[workflow_id] = workflow
        logger.info(f"Workflow V2.0 created: {workflow_id}")
        
        return workflow
    
    async def update_workflow(self, workflow_id: str, **updates) -> Workflow:
        """更新工作流"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        if "name" in updates:
            workflow.name = updates["name"]
        if "description" in updates:
            workflow.description = updates["description"]
        if "nodes" in updates:
            workflow.nodes = [WorkflowNode(**n) for n in updates["nodes"]]
        if "edges" in updates:
            workflow.edges = [WorkflowEdge(**e) for e in updates["edges"]]
        if "enabled" in updates:
            workflow.enabled = updates["enabled"]
        if "max_parallel" in updates:
            workflow.max_parallel = updates["max_parallel"]
        if "error_handling" in updates:
            workflow.error_handling = updates["error_handling"]
        
        workflow.updated_at = datetime.now()
        workflow.version += 1
        
        return workflow
    
    async def execute(self, workflow_id: str, input_variables: Optional[Dict] = None) -> ExecutionContext:
        """执行工作流"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        execution_id = f"exec-{uuid.uuid4().hex[:8]}"
        context = ExecutionContext(
            execution_id=execution_id,
            workflow_id=workflow_id,
            variables=input_variables or {},
        )
        
        self.execution_contexts[execution_id] = context
        self._running_executions.add(execution_id)
        
        # 启动异步执行
        asyncio.create_task(self._execute_workflow(workflow, context))
        
        return context
    
    async def execute_sync(self, workflow_id: str, input_variables: Optional[Dict] = None) -> ExecutionContext:
        """同步执行工作流"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        execution_id = f"exec-{uuid.uuid4().hex[:8]}"
        context = ExecutionContext(
            execution_id=execution_id,
            workflow_id=workflow_id,
            variables=input_variables or {},
        )
        
        self.execution_contexts[execution_id] = context
        
        await self._execute_workflow(workflow, context)
        
        return context
    
    async def _execute_workflow(self, workflow: Workflow, context: ExecutionContext):
        """执行工作流核心逻辑"""
        dag = DAGExecutor(workflow, self._executors)
        max_parallel = workflow.max_parallel
        
        try:
            while True:
                pending = sum(1 for s in context.node_statuses.values() if s == NodeStatus.PENDING)
                running = sum(1 for s in context.node_statuses.values() if s == NodeStatus.RUNNING)
                waiting = sum(1 for s in context.node_statuses.values() if s == NodeStatus.WAITING)
                
                if pending == 0 and running == 0:
                    end_nodes = [n for n in workflow.nodes if n.node_type == NodeType.END]
                    if all(context.node_statuses.get(n.node_id) == NodeStatus.COMPLETED for n in end_nodes):
                        context.status = NodeStatus.COMPLETED
                        break
                    for end_node in end_nodes:
                        if end_node.node_id not in context.node_statuses:
                            context.node_statuses[end_node.node_id] = NodeStatus.COMPLETED
                    continue
                
                parallel_nodes = dag.get_parallel_nodes(context, max_parallel)
                
                if not parallel_nodes:
                    if running > 0 or waiting > 0:
                        await asyncio.sleep(0.1)
                        continue
                    else:
                        # 死锁诊断
                        stuck = self._diagnose_dead_end(workflow, dag, context)
                        context.status = NodeStatus.FAILED
                        context.error = stuck["message"]
                        logger.error(f"Workflow dead end: {stuck}")
                        break
                
                # 并行执行节点
                tasks = []
                for node_id in parallel_nodes:
                    tasks.append(self._execute_node(workflow, dag, context, node_id))
                
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # 保存检查点
                await self._persist_checkpoint(context)
                await asyncio.sleep(0.01)
            
        except Exception as e:
            context.status = NodeStatus.FAILED
            context.error = str(e)
            logger.error(f"Workflow execution failed: {e}")
        
        finally:
            context.completed_at = datetime.now()
            self._running_executions.discard(context.execution_id)
            await self._persist_checkpoint(context)
    
    def _diagnose_dead_end(self, workflow: Workflow, dag: DAGExecutor, context: ExecutionContext) -> Dict[str, Any]:
        """诊断死端 — 返回哪个节点卡住及原因"""
        unstarted = [nid for nid, s in context.node_statuses.items()
                     if s in (NodeStatus.PENDING, NodeStatus.WAITING)]
        stuck_nodes = []
        for node_id in unstarted:
            node = dag._node_map.get(node_id)
            if not node:
                continue
            predecessors = [e.source for e in dag._in_edges.get(node_id, [])]
            pred_statuses = {p: context.node_statuses.get(p) for p in predecessors}
            # 检查是条件节点还是真正的死端
            reasons = []
            if not predecessors:
                reasons.append("no incoming edges (root node)")
            else:
                for pred, status in pred_statuses.items():
                    if status is None:
                        reasons.append(f"predecessor '{pred}' never executed")
                    elif status == NodeStatus.PENDING:
                        reasons.append(f"predecessor '{pred}' pending")
                    elif status == NodeStatus.FAILED:
                        reasons.append(f"predecessor '{pred}' failed")
                    elif status == NodeStatus.WAITING:
                        reasons.append(f"predecessor '{pred}' waiting")
                    elif status == NodeStatus.SKIPPED:
                        reasons.append(f"predecessor '{pred}' skipped")
            is_conditional = node.node_type in (NodeType.CONDITION, NodeType.BRANCH)
            stuck_nodes.append({
                "node_id": node_id,
                "node_name": node.name,
                "node_type": node.node_type.value,
                "is_conditional": is_conditional,
                "reasons": reasons,
            })
        message = f"Deadlock: no ready nodes. Stuck nodes: {len(stuck_nodes)} — " + \
                  ", ".join(f"{n['node_name']} ({n['node_type']}: {'; '.join(n['reasons'])})" for n in stuck_nodes[:5])
        return {"message": message, "stuck_nodes": stuck_nodes}
    
    async def _execute_node(
        self,
        workflow: Workflow,
        dag: DAGExecutor,
        context: ExecutionContext,
        node_id: str,
    ):
        """执行单个节点"""
        node = dag._node_map[node_id]
        context.node_statuses[node_id] = NodeStatus.RUNNING
        context.execution_path.append(node_id)
        
        logger.debug(f"Executing node: {node.name} ({node.node_type.value})")
        
        executor = self._executors.get(node.node_type)
        max_retries = node.retry_config.get("max_retries", 0)
        retry_delay = node.retry_config.get("delay", 1)
        timeout = getattr(node, 'timeout', 300) or 300
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    context.node_statuses[node_id] = NodeStatus.RETRYING
                    logger.info(f"Retrying node {node_id}, attempt {attempt}")
                    await asyncio.sleep(retry_delay * attempt)
                
                if executor:
                    result = await asyncio.wait_for(
                        executor.execute(node, context),
                        timeout=timeout
                    )
                else:
                    result = {"success": True, "result": "no executor"}
                
                context.node_results[node_id] = result
                
                if result.get("success", True):
                    context.node_statuses[node_id] = NodeStatus.COMPLETED
                    logger.debug(f"Node completed: {node.name}")
                    return
                else:
                    error = result.get("error", "Unknown error")
                    if attempt == max_retries:
                        raise Exception(f"Node failed: {error}")
                    logger.warning(f"Node failed, will retry: {error}")
                    
            except asyncio.TimeoutError:
                logger.error(f"Node {node_id} timed out after {timeout}s")
                context.node_statuses[node_id] = NodeStatus.FAILED
                context.node_results[node_id] = {"error": f"Timeout after {timeout}s"}
                if workflow.error_handling == "stop":
                    context.status = NodeStatus.FAILED
                    context.error = f"Node {node_id} timed out after {timeout}s"
                    raise
                elif workflow.error_handling in ("skip", "continue"):
                    context.node_statuses[node_id] = NodeStatus.SKIPPED
                return
                    
            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"Node failed after {max_retries} retries: {node_id}")
                    context.node_statuses[node_id] = NodeStatus.FAILED
                    context.node_results[node_id] = {"error": str(e)}
                    
                    if workflow.error_handling == "stop":
                        context.status = NodeStatus.FAILED
                        context.error = f"Node {node_id} failed: {e}"
                    elif workflow.error_handling in ("skip", "continue"):
                        context.node_statuses[node_id] = NodeStatus.SKIPPED
                else:
                    logger.warning(f"Node error, will retry: {e}")
        
        if workflow.error_handling in ("skip", "continue"):
            for edge in dag._out_edges.get(node_id, []):
                if edge.target not in context.node_statuses:
                    context.node_statuses[edge.target] = NodeStatus.SKIPPED
    
    async def _persist_checkpoint(self, context: ExecutionContext):
        """保存执行检查点（Redis JSON）"""
        if not self._redis_client:
            return
        try:
            data = {
                "execution_id": context.execution_id,
                "workflow_id": context.workflow_id,
                "status": context.status.value,
                "variables": context.variables,
                "node_results": context.node_results,
                "node_statuses": {k: v.value for k, v in context.node_statuses.items()},
                "retry_counts": context.retry_counts,
                "execution_path": context.execution_path,
                "checkpoint_at": datetime.now().isoformat(),
            }
            key = f"wanclaw:exec:{context.execution_id}"
            self._redis_client.set(key, json.dumps(data, default=str))
        except Exception as e:
            logger.warning(f"Checkpoint persist failed: {e}")
    
    async def persist_workflows(self) -> bool:
        """持久化所有工作流到Redis"""
        if not self._redis_client:
            logger.warning("Redis not available, cannot persist workflows")
            return False
        try:
            workflows_data = []
            for wf in self.workflows.values():
                wf_dict = {
                    "workflow_id": wf.workflow_id,
                    "name": wf.name,
                    "description": wf.description,
                    "nodes": [asdict(n) for n in wf.nodes],
                    "edges": [asdict(e) for e in wf.edges],
                    "trigger": wf.trigger.value,
                    "schedule": wf.schedule,
                    "enabled": wf.enabled,
                    "version": wf.version,
                    "max_parallel": wf.max_parallel,
                    "error_handling": wf.error_handling,
                    "created_at": wf.created_at.isoformat() if wf.created_at else None,
                    "updated_at": wf.updated_at.isoformat() if wf.updated_at else None,
                    "last_run_at": wf.last_run_at.isoformat() if wf.last_run_at else None,
                }
                workflows_data.append(wf_dict)
            self._redis_client.set("wanclaw:workflows", json.dumps(workflows_data, default=str))
            logger.info(f"Persisted {len(workflows_data)} workflows")
            return True
        except Exception as e:
            logger.error(f"Persist workflows failed: {e}")
            return False
    
    async def load_workflows(self) -> int:
        """从Redis加载工作流，返回加载数量"""
        if not self._redis_client:
            return 0
        try:
            data = self._redis_client.get("wanclaw:workflows")
            if not data:
                return 0
            workflows_list = json.loads(str(data))
            for wf_dict in workflows_list:
                if wf_dict.get("nodes"):
                    wf_dict["nodes"] = [WorkflowNode(**n) for n in wf_dict["nodes"]]
                if wf_dict.get("edges"):
                    wf_dict["edges"] = [WorkflowEdge(**e) for e in wf_dict["edges"]]
                if wf_dict.get("trigger"):
                    wf_dict["trigger"] = TriggerType(wf_dict["trigger"])
                if wf_dict.get("created_at"):
                    wf_dict["created_at"] = datetime.fromisoformat(wf_dict["created_at"])
                if wf_dict.get("updated_at"):
                    wf_dict["updated_at"] = datetime.fromisoformat(wf_dict["updated_at"])
                if wf_dict.get("last_run_at") and wf_dict["last_run_at"]:
                    wf_dict["last_run_at"] = datetime.fromisoformat(wf_dict["last_run_at"])
                wf = Workflow(**wf_dict)
                self.workflows[wf.workflow_id] = wf
            logger.info(f"Loaded {len(workflows_list)} workflows from Redis")
            return len(workflows_list)
        except Exception as e:
            logger.error(f"Load workflows failed: {e}")
            return 0
    
    async def resume_execution(self, execution_id: str) -> Optional[ExecutionContext]:
        """从Redis检查点恢复执行"""
        if not self._redis_client:
            return None
        try:
            key = f"wanclaw:exec:{execution_id}"
            data = self._redis_client.get(key)
            if not data:
                return None
            ctx_dict = json.loads(str(data))
            ctx_dict["status"] = NodeStatus(ctx_dict["status"])
            ctx_dict["node_statuses"] = {k: NodeStatus(v) for k, v in ctx_dict["node_statuses"].items()}
            ctx_dict["started_at"] = datetime.fromisoformat(ctx_dict["started_at"]) if ctx_dict.get("started_at") else datetime.now()
            ctx_dict["checkpoint_at"] = datetime.fromisoformat(ctx_dict["checkpoint_at"]) if ctx_dict.get("checkpoint_at") else None
            context = ExecutionContext(**ctx_dict)
            self.execution_contexts[execution_id] = context
            self._running_executions.add(execution_id)
            workflow = self.workflows.get(context.workflow_id)
            if workflow:
                asyncio.create_task(self._execute_workflow(workflow, context))
            logger.info(f"Resumed execution {execution_id} from checkpoint")
            return context
        except Exception as e:
            logger.error(f"Resume execution failed: {e}")
            return None
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """取消执行"""
        if execution_id in self._running_executions:
            context = self.execution_contexts.get(execution_id)
            if context:
                context.status = NodeStatus.FAILED
                context.error = "Cancelled by user"
                context.completed_at = datetime.now()
                self._running_executions.discard(execution_id)
                return True
        return False
    
    async def get_execution(self, execution_id: str) -> Optional[ExecutionContext]:
        """获取执行上下文"""
        return self.execution_contexts.get(execution_id)
    
    async def list_workflows(self, enabled: Optional[bool] = None) -> List[Workflow]:
        """列出工作流"""
        workflows = list(self.workflows.values())
        if enabled is not None:
            workflows = [w for w in workflows if w.enabled == enabled]
        return workflows
    
    async def start_scheduler(self):
        """启动调度器"""
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Workflow scheduler V2.0 started")
    
    async def stop_scheduler(self):
        """停止调度器"""
        if self._scheduler_task:
            self._scheduler_task.cancel()
    
    async def _scheduler_loop(self):
        """调度循环"""
        while True:
            try:
                now = datetime.now()
                for workflow in self.workflows.values():
                    if workflow.trigger == TriggerType.SCHEDULED and workflow.enabled:
                        if self._should_run(workflow, now):
                            workflow.last_run_at = now
                            await self.execute(workflow.workflow_id)
                
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)
    
    def _should_run(self, workflow: Workflow, now: Optional[datetime] = None) -> bool:
        """检查是否应该运行"""
        if not workflow.schedule:
            return False
        now = now or datetime.now()
        if workflow.last_run_at and (now - workflow.last_run_at).total_seconds() < 30:
            return False
        if CRONITER_AVAILABLE:
            try:
                from croniter import croniter as cron_class
                cron = cron_class(workflow.schedule, now)
                prev = cron.get_prev(datetime)
                next_run = cron.get_next(datetime)
                if prev <= now < next_run:
                    return True
                return False
            except Exception as e:
                logger.warning(f"Invalid CRON schedule '{workflow.schedule}': {e}")
                return False
        else:
            return False
    
    async def validate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """验证工作流"""
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return {"valid": False, "errors": ["Workflow not found"]}
        
        errors = []
        warnings = []
        
        start_nodes = [n for n in workflow.nodes if n.node_type == NodeType.START]
        if not start_nodes:
            errors.append("No start node")
        
        end_nodes = [n for n in workflow.nodes if n.node_type == NodeType.END]
        if not end_nodes:
            warnings.append("No end node")
        
        connected = set()
        for edge in workflow.edges:
            connected.add(edge.source)
            connected.add(edge.target)
        
        for node in workflow.nodes:
            if node.node_id not in connected and node.node_type not in [NodeType.START, NodeType.END]:
                warnings.append(f"Disconnected node: {node.name}")
        
        for node in workflow.nodes:
            executor = self._executors.get(node.node_type)
            if executor:
                try:
                    if not await executor.validate(node):
                        errors.append(f"Invalid config for node: {node.name}")
                except:
                    pass
        
        dag = DAGExecutor(workflow, self._executors)
        cycle_info = dag.get_cycle_info()
        if cycle_info["has_cycle"]:
            cycle_names = [dag._node_map[nid].name for nid in cycle_info["cycle_nodes"]]
            errors.append(
                f"Workflow contains cycles: nodes {cycle_info['cycle_nodes']} "
                f"(names: {cycle_names}) forming path {' -> '.join(cycle_info['cycle_path'])}"
            )
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "cycle_info": cycle_info if cycle_info["has_cycle"] else None,
        }


class NodeExecutor(ABC):
    """节点执行器基类"""
    
    @abstractmethod
    async def execute(self, node: WorkflowNode, context: ExecutionContext) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def validate(self, node: WorkflowNode) -> bool:
        pass


class DefaultExecutor(NodeExecutor):
    """默认执行器"""
    
    async def execute(self, node: WorkflowNode, context: ExecutionContext) -> Dict[str, Any]:
        return {"success": True, "result": "default"}
    
    async def validate(self, node: WorkflowNode) -> bool:
        return True


def _resolve_var(expr: str, context: ExecutionContext) -> Any:
    """Enhanced variable substitution: nested access, array index, filters, defaults, node results."""
    raw = expr
    default_val = None
    default = None
    
    # Default value: ${name|30}
    if '|' in expr:
        parts = expr.split('|', 1)
        check_path = parts[0]
        # Check if it's a filter or a default
        if not any(f in parts[1].lower() for f in ('upper', 'lower', 'int', 'float', 'str', 'bool', 'length', 'default')):
            expr = check_path
            default_val = parts[1]
            try:
                default = ast.literal_eval(default_val)
            except Exception:
                default = default_val
    
    # Extract parts: path, filter, index
    filter_name = None
    path = expr
    
    # Filter: ${name|upper} or ${user.name|upper}
    if '|' in expr:
        path, filter_name = expr.split('|', 1)
    
    # Node result access: ${node_id.result}
    if '.' in path and not path.startswith('user') and not path.startswith('item'):
        parts = path.split('.', 1)
        if parts[0] in context.node_results:
            val = context.node_results[parts[0]].get(parts[1], None)
            return _apply_filter(val, filter_name, raw, default)
    
    # Nested/nested access: ${user.name}
    if '.' in path:
        parts = path.split('.')
        val = context.variables
        for part in parts:
            if val is None:
                break
            if isinstance(val, dict):
                val = val.get(part)
            else:
                val = getattr(val, part, None)
        return _apply_filter(val, filter_name, raw, default)
    
    # Array index: ${items[0]}
    idx_match = re.match(r'^([^\[]+)\[(\d+)\]$', path)
    if idx_match:
        base_name = idx_match.group(1)
        idx = int(idx_match.group(2))
        container = context.variables.get(base_name, [])
        if isinstance(container, (list, tuple)) and 0 <= idx < len(container):
            val = container[idx]
            return _apply_filter(val, filter_name, raw, default)
        return _apply_filter(None, filter_name, raw, default)
    
    # Simple variable
    val = context.variables.get(path)
    if val is None:
        val = default
    return _apply_filter(val, filter_name, raw, default)


def _apply_filter(val: Any, filter_name: Optional[str], raw: str, default: Any) -> Any:
    """Apply a filter to a value."""
    if filter_name is None:
        return val
    f = filter_name.lower()
    if f == 'upper':
        return str(val).upper() if val is not None else default
    if f == 'lower':
        return str(val).lower() if val is not None else default
    if f == 'int':
        return int(val) if val is not None else default
    if f == 'float':
        return float(val) if val is not None else default
    if f == 'str':
        return str(val) if val is not None else default
    if f == 'bool':
        return bool(val) if val is not None else default
    if f == 'length':
        return len(val) if val is not None else 0
    if f == 'default':
        return default
    return val


class TaskExecutor(NodeExecutor):
    """任务节点执行器"""
    
    def __init__(self, task_executor):
        self.task_executor = task_executor
    
    async def execute(self, node: WorkflowNode, context: ExecutionContext) -> Dict[str, Any]:
        task_config = node.config
        task_name = task_config.get("task_name")
        params = task_config.get("params", {})
        
        params = self._resolve_variables(params, context)
        
        if self.task_executor:
            result = await self.task_executor.execute_now(task_name, params)
            return {"success": True, "result": result.result, "task_id": result.task_id}
        
        return {"success": False, "error": "Task executor not available"}
    
    async def validate(self, node: WorkflowNode) -> bool:
        return "task_name" in node.config
    
    def _resolve_variables(self, data: Any, context: ExecutionContext) -> Any:
        if isinstance(data, dict):
            return {k: self._resolve_variables(v, context) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._resolve_variables(v, context) for v in data]
        elif isinstance(data, str) and data.startswith("${") and data.endswith("}"):
            return _resolve_var(data[2:-1], context)
        return data


class ConditionExecutor(NodeExecutor):
    """条件节点执行器"""
    
    def __init__(self, llm_client=None):
        self.llm = llm_client
    
    async def execute(self, node: WorkflowNode, context: ExecutionContext) -> Dict[str, Any]:
        condition = node.config.get("condition", "")
        condition = self._resolve_condition(condition, context)
        result = self._evaluate_condition(condition, context)
        
        return {"success": True, "result": result, "branch": "true" if result else "false"}
    
    async def validate(self, node: WorkflowNode) -> bool:
        return "condition" in node.config
    
    def _resolve_condition(self, condition: str, context: ExecutionContext) -> str:
        pattern = r'\$\{([^}]+)\}'
        def replacer(match):
            var_expr = match.group(1)
            val = _resolve_var(var_expr, context)
            return str(val) if val is not None else ''
        return re.sub(pattern, replacer, condition)
    
    def _evaluate_condition(self, condition: str, context: ExecutionContext) -> bool:
        try:
            return self._parse_expr(condition.strip())
        except Exception:
            return False
    
    def _parse_expr(self, s: str) -> bool:
        s = s.strip()
        # Handle 'or' (lowest precedence)
        or_parts = self._split_by_op(s, ' or ')
        if len(or_parts) > 1:
            return any(self._parse_expr(p) for p in or_parts)
        # Handle 'and'
        and_parts = self._split_by_op(s, ' and ')
        if len(and_parts) > 1:
            return all(self._parse_expr(p) for p in and_parts)
        # Handle 'not'
        if s.startswith('not '):
            return not self._parse_expr(s[4:].strip())
        # Handle comparisons
        for op in ['==', '!=', '>=', '<=', '>', '<']:
            idx = s.find(op)
            if idx != -1:
                left = self._parse_value(s[:idx].strip())
                right = self._parse_value(s[idx + len(op):].strip())
                return self._apply_cmp(op, left, right)
        # Handle 'in'
        if ' in ' in s:
            parts = s.split(' in ', 1)
            left = self._parse_value(parts[0].strip())
            right = self._parse_value(parts[1].strip())
            if isinstance(right, (list, tuple, str, dict, set)):
                return left in right  # type: ignore[reportOperatorIssue]
            return False
        # Handle 'startswith' / 'endswith'
        if s.endswith('.startswith('):
            idx = s.find('.startswith(')
            left = str(self._parse_value(s[:idx].strip()))
            right = str(self._parse_value(s[idx + 12:-1].strip()))
            return left.startswith(right)
        if s.endswith('.endswith('):
            idx = s.find('.endswith(')
            left = str(self._parse_value(s[:idx].strip()))
            right = str(self._parse_value(s[idx + 10:-1].strip()))
            return left.endswith(right)
        # Boolean literal
        if s == 'True':
            return True
        if s == 'False':
            return False
        # Parenthesized expression
        if s.startswith('(') and s.endswith(')'):
            return self._parse_expr(s[1:-1])
        return bool(self._parse_value(s))
    
    def _split_by_op(self, s: str, op: str) -> List[str]:
        parts = []
        depth = 0
        start = 0
        i = 0
        while i < len(s):
            c = s[i]
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
            elif depth == 0 and s[i:i+len(op)] == op:
                parts.append(s[start:i])
                i += len(op)
                start = i
                continue
            i += 1
        parts.append(s[start:])
        return parts
    
    def _parse_value(self, s: str):
        s = s.strip()
        if not s:
            return None
        if s == 'True':
            return True
        if s == 'False':
            return False
        try:
            if '.' in s:
                return float(s)
            return int(s)
        except ValueError:
            pass
        if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
            return s[1:-1]
        # Try list/dict literal
        if (s.startswith('[') and s.endswith(']')) or (s.startswith('{') and s.endswith('}')):
            try:
                return ast.literal_eval(s)
            except Exception:
                pass
        return s
    
    def _apply_cmp(self, op: str, left: Any, right: Any) -> bool:
        if op == '==':
            return left == right
        if op == '!=':
            return left != right
        if op == '>':
            return left > right
        if op == '<':
            return left < right
        if op == '>=':
            return left >= right
        if op == '<=':
            return left <= right
        return False


class SkillExecutor(NodeExecutor):
    """技能节点执行器"""
    
    def __init__(self, skill_manager):
        self.skill_manager = skill_manager
    
    async def execute(self, node: WorkflowNode, context: ExecutionContext) -> Dict[str, Any]:
        skill_config = node.config
        skill_name = skill_config.get("skill_name")
        params = skill_config.get("params", {})
        
        params = self._resolve_variables(params, context)
        
        if self.skill_manager:
            result = await self.skill_manager.execute(skill_name, params)
            return {"success": True, "result": result}
        
        return {"success": False, "error": "Skill manager not available"}
    
    async def validate(self, node: WorkflowNode) -> bool:
        return "skill_name" in node.config
    
    def _resolve_variables(self, data: Any, context: ExecutionContext) -> Any:
        if isinstance(data, dict):
            return {k: self._resolve_variables(v, context) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._resolve_variables(v, context) for v in data]
        elif isinstance(data, str) and data.startswith("${") and data.endswith("}"):
            return _resolve_var(data[2:-1], context)
        return data


class HTTPExecutor(NodeExecutor):
    """HTTP节点执行器"""
    
    def __init__(self, http_client=None):
        self.http_client = http_client
    
    async def execute(self, node: WorkflowNode, context: ExecutionContext) -> Dict[str, Any]:
        http_config = node.config
        method = http_config.get("method", "GET")
        url = http_config.get("url", "")
        headers = http_config.get("headers", {})
        body = http_config.get("body", {})
        
        url = self._resolve_variable(url, context)
        
        if self.http_client:
            try:
                if method.upper() == "GET":
                    response = await self.http_client.get(url, headers=headers)
                else:
                    response = await self.http_client.request(method, url, headers=headers, json=body)
                
                return {"success": True, "status": response.status_code, "body": response.json()}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "HTTP client not available"}
    
    async def validate(self, node: WorkflowNode) -> bool:
        return "url" in node.config
    
    def _resolve_variable(self, data: str, context: ExecutionContext) -> str:
        if isinstance(data, str) and data.startswith("${") and data.endswith("}"):
            val = _resolve_var(data[2:-1], context)
            return str(val) if val is not None else data
        return data


class WaitExecutor(NodeExecutor):
    """等待节点执行器"""
    
    async def execute(self, node: WorkflowNode, context: ExecutionContext) -> Dict[str, Any]:
        wait_config = node.config
        duration = wait_config.get("duration", 5)
        
        await asyncio.sleep(duration)
        
        return {"success": True, "waited": duration}
    
    async def validate(self, node: WorkflowNode) -> bool:
        return "duration" in node.config


class ParallelExecutor(NodeExecutor):
    """并行节点执行器"""
    
    def __init__(self, executors: Dict[NodeType, NodeExecutor]):
        self.executors = executors
    
    async def execute(self, node: WorkflowNode, context: ExecutionContext) -> Dict[str, Any]:
        parallel_config = node.config
        branches = parallel_config.get("branches", [])
        
        tasks = []
        for branch in branches:
            sub_context = ExecutionContext(
                execution_id=f"{context.execution_id}-{branch['node_id']}",
                workflow_id=context.workflow_id,
                variables=context.variables.copy(),
            )
            
            executor = self.executors.get(NodeType(branch.get("type", "task")))
            if executor:
                tasks.append(executor.execute(branch, sub_context))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {"success": True, "results": results}
    
    async def validate(self, node: WorkflowNode) -> bool:
        return len(node.config.get("branches", [])) > 0


# 全局实例
_workflow_engine: Optional[WorkflowEngine] = None


def get_workflow_engine() -> WorkflowEngine:
    """获取工作流引擎单例"""
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine()
    return _workflow_engine