"""
工作流链技能
多轮任务流程自动化（备份→压缩→发邮件→记录日志，一键执行）
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from wanclaw.backend.skills import BaseSkill, SkillResult, SkillCategory, SkillLevel


logger = logging.getLogger(__name__)


class WorkflowChainSkill(BaseSkill):
    """工作流链技能"""
    
    def __init__(self):
        super().__init__()
        self.name = "WorkflowChain"
        self.description = "工作流链：多轮任务流程自动化，一键执行复杂任务链"
        self.category = SkillCategory.AI
        self.level = SkillLevel.ADVANCED
        
        self.required_params = ["action"]
        
        self.optional_params = {
            "workflow_name": str,
            "steps": list,
            "params": dict,
            "parallel": bool,
            "save_workflow": bool,
            "workflow_id": str
        }
    
    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        action = params.get("action", "").lower()
        
        try:
            if action == "execute":
                return await self._execute_workflow(params)
            elif action == "create":
                return await self._create_workflow(params)
            elif action == "list":
                return await self._list_workflows(params)
            elif action == "status":
                return await self._workflow_status(params)
            else:
                return SkillResult(
                    success=False,
                    message=f"不支持的操作: {action}",
                    error=f"Unsupported action: {action}"
                )
        except Exception as e:
            logger.error(f"工作流链失败: {action} - {e}")
            return SkillResult(
                success=False,
                message=f"工作流链失败: {str(e)}",
                error=str(e)
            )
    
    async def _execute_workflow(self, params: Dict[str, Any]) -> SkillResult:
        workflow_name = params.get("workflow_name", "")
        steps = params.get("steps", [])
        parallel = params.get("parallel", False)
        
        if not steps:
            steps = [
                {"skill": "Backup", "action": "create", "params": {"source_path": "/data", "backup_path": "/backup"}},
                {"skill": "BatchFileProcessor", "action": "compress", "params": {"source_path": "/backup", "compress_format": "tar.gz"}},
                {"skill": "EmailAutomation", "action": "batch_send", "params": {"recipients": ["admin@company.com"], "subject": "备份完成通知"}},
                {"skill": "LogViewer", "action": "search", "params": {"log_path": "/var/log/syslog", "search_pattern": "backup"}}
            ]
        
        mock_results = []
        for i, step in enumerate(steps):
            mock_results.append({
                "step": i + 1,
                "skill": step["skill"],
                "action": step["action"],
                "status": "success",
                "duration_seconds": 5 + i * 2,
                "output": f"Step {i+1} completed successfully",
                "timestamp": datetime.now().isoformat()
            })
        
        total_duration = sum(r["duration_seconds"] for r in mock_results)
        
        return SkillResult(
            success=True,
            message=f"工作流执行完成，{len(steps)}个步骤全部成功",
            data={
                "workflow_name": workflow_name or "unnamed_workflow",
                "steps": mock_results,
                "total_steps": len(steps),
                "successful_steps": len([r for r in mock_results if r["status"] == "success"]),
                "failed_steps": len([r for r in mock_results if r["status"] == "failed"]),
                "total_duration_seconds": total_duration,
                "executed_at": datetime.now().isoformat(),
                "parallel": parallel,
                "note": "工作流执行，当前返回模拟数据"
            }
        )
    
    async def _create_workflow(self, params: Dict[str, Any]) -> SkillResult:
        workflow_name = params.get("workflow_name", "自定义工作流")
        steps = params.get("steps", [])
        save_workflow = params.get("save_workflow", True)
        
        workflow_id = f"wf_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        if not steps:
            steps = [
                {"step": 1, "skill": "Backup", "action": "create", "params": {"source_path": "/data"}, "depends_on": None},
                {"step": 2, "skill": "BatchFileProcessor", "action": "compress", "params": {}, "depends_on": 1},
                {"step": 3, "skill": "EmailAutomation", "action": "batch_send", "params": {}, "depends_on": 2}
            ]
        
        workflow = {
            "workflow_id": workflow_id,
            "workflow_name": workflow_name,
            "steps": steps,
            "total_steps": len(steps),
            "can_parallelize": self._check_parallel(steps),
            "estimated_duration_seconds": len(steps) * 30,
            "created_at": datetime.now().isoformat(),
            "enabled": True
        }
        
        return SkillResult(
            success=True,
            message=f"工作流创建完成: {workflow_name}",
            data={
                "workflow": workflow,
                "workflow_id": workflow_id,
                "saved": save_workflow,
                "note": "工作流创建，当前返回模拟数据"
            }
        )
    
    async def _list_workflows(self, params: Dict[str, Any]) -> SkillResult:
        mock_workflows = [
            {"workflow_id": "wf_20240115_001", "name": "每日备份工作流", "steps": 4, "last_run": "2024-01-15 02:00", "status": "active"},
            {"workflow_id": "wf_20240114_001", "name": "周报生成工作流", "steps": 3, "last_run": "2024-01-14 09:00", "status": "active"},
            {"workflow_id": "wf_20240110_001", "name": "竞品监控工作流", "steps": 5, "last_run": "2024-01-10 10:00", "status": "active"},
            {"workflow_id": "wf_20240105_001", "name": "考勤汇总工作流", "steps": 2, "last_run": "2024-01-05 18:00", "status": "paused"}
        ]
        
        return SkillResult(
            success=True,
            message=f"找到{len(mock_workflows)}个工作流",
            data={
                "workflows": mock_workflows,
                "total": len(mock_workflows),
                "active": len([w for w in mock_workflows if w["status"] == "active"]),
                "paused": len([w for w in mock_workflows if w["status"] == "paused"]),
                "note": "工作流列表，当前返回模拟数据"
            }
        )
    
    async def _workflow_status(self, params: Dict[str, Any]) -> SkillResult:
        workflow_id = params.get("workflow_id", "")
        
        mock_status = {
            "workflow_id": workflow_id or "wf_latest",
            "name": "每日备份工作流",
            "status": "idle",
            "current_step": None,
            "last_run": {
                "started_at": "2024-01-15 02:00:00",
                "completed_at": "2024-01-15 02:05:32",
                "duration_seconds": 332,
                "result": "success",
                "steps_completed": 4,
                "steps_failed": 0
            },
            "next_scheduled_run": "2024-01-16 02:00:00",
            "total_runs": 15,
            "success_rate": 93.3
        }
        
        return SkillResult(
            success=True,
            message=f"工作流状态: {mock_status['status']}",
            data={
                "status": mock_status,
                "note": "工作流状态，当前返回模拟数据"
            }
        )
    
    def _check_parallel(self, steps: List[Dict]) -> bool:
        for step in steps:
            if step.get("depends_on") is not None:
                return False
        return True
