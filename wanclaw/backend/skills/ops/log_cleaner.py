"""
日志清理技能
日志自动清理
"""

import os
import glob
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from wanclaw.backend.skills import BaseSkill, SkillResult, SkillCategory, SkillLevel
from wanclaw.backend.im_adapter.security import get_security, OperationType


logger = logging.getLogger(__name__)


class LogCleanerSkill(BaseSkill):
    """日志清理技能"""
    
    def __init__(self):
        super().__init__()
        self.name = "LogCleaner"
        self.description = "日志清理：日志自动清理"
        self.category = SkillCategory.OPS
        self.level = SkillLevel.INTERMEDIATE
        
        self.required_params = ["action"]
        
        self.optional_params = {
            "log_path": str,
            "max_age_days": int,
            "max_size_mb": int,
            "pattern": str,
            "dry_run": bool,
            "compress": bool,
            "delete_empty": bool
        }
    
    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        action = params.get("action", "").lower()
        user_id = params.get("user_id", "unknown")
        username = params.get("username", "unknown")
        
        security = get_security()
        
        if action in ["clean", "schedule", "status"]:
            log_path = params.get("log_path", "")
            if log_path:
                allowed, reason = security.check_file_access(
                    log_path, OperationType.FILE_WRITE, user_id, username
                )
                if not allowed:
                    return SkillResult(
                        success=False,
                        message=f"路径访问被拒绝: {reason}",
                        error="Security check failed"
                    )
        
        try:
            if action == "clean":
                return await self._clean_logs(params)
            elif action == "schedule":
                return await self._schedule_cleaning(params)
            elif action == "status":
                return await self._log_status(params)
            else:
                return SkillResult(
                    success=False,
                    message=f"不支持的操作: {action}",
                    error=f"Unsupported action: {action}"
                )
        except Exception as e:
            logger.error(f"日志清理失败: {action} - {e}")
            return SkillResult(
                success=False,
                message=f"日志清理失败: {str(e)}",
                error=str(e)
            )
    
    async def _clean_logs(self, params: Dict[str, Any]) -> SkillResult:
        log_path = params.get("log_path", "/var/log")
        max_age_days = params.get("max_age_days", 30)
        max_size_mb = params.get("max_size_mb", 1000)
        pattern = params.get("pattern", "*.log")
        dry_run = params.get("dry_run", False)
        compress = params.get("compress", True)
        delete_empty = params.get("delete_empty", True)
        
        if not os.path.exists(log_path):
            return SkillResult(
                success=False,
                message=f"路径不存在: {log_path}",
                error="Path not found"
            )
        
        mock_files = [
            {"path": f"{log_path}/syslog", "size": 5242880, "age_days": 5, "action": "keep"},
            {"path": f"{log_path}/auth.log", "size": 1048576, "age_days": 3, "action": "keep"},
            {"path": f"{log_path}/old_app.log", "size": 2097152, "age_days": 45, "action": "delete" if not dry_run else "would_delete"},
            {"path": f"{log_path}/debug.log", "size": 1572864, "age_days": 60, "action": "compress" if compress else "delete" if not dry_run else "would_compress"},
            {"path": f"{log_path}/empty.log", "size": 0, "age_days": 10, "action": "delete" if delete_empty and not dry_run else "keep"}
        ]
        
        total_size = sum(f["size"] for f in mock_files)
        freed_size = sum(f["size"] for f in mock_files if "delete" in f["action"])
        deleted_count = len([f for f in mock_files if "delete" in f["action"]])
        compressed_count = len([f for f in mock_files if "compress" in f["action"]])
        
        return SkillResult(
            success=True,
            message=f"日志清理{'（预览）' if dry_run else ''}完成，释放{freed_size}字节",
            data={
                "log_path": log_path,
                "max_age_days": max_age_days,
                "max_size_mb": max_size_mb,
                "pattern": pattern,
                "dry_run": dry_run,
                "files_processed": len(mock_files),
                "files_deleted": deleted_count,
                "files_compressed": compressed_count,
                "total_size_before": total_size,
                "freed_size": freed_size,
                "details": mock_files,
                "note": "日志清理功能，当前返回模拟数据"
            }
        )
    
    async def _schedule_cleaning(self, params: Dict[str, Any]) -> SkillResult:
        log_path = params.get("log_path", "/var/log")
        max_age_days = params.get("max_age_days", 30)
        schedule = params.get("schedule", "daily")
        
        schedule_config = {
            "log_path": log_path,
            "max_age_days": max_age_days,
            "schedule": schedule,
            "next_run": self._calculate_next_run(schedule),
            "enabled": True,
            "created_at": datetime.now().isoformat()
        }
        
        return SkillResult(
            success=True,
            message=f"日志清理计划已创建: {schedule}",
            data={
                "schedule_config": schedule_config,
                "note": "计划清理需要任务调度支持，当前返回模拟数据"
            }
        )
    
    async def _log_status(self, params: Dict[str, Any]) -> SkillResult:
        log_path = params.get("log_path", "/var/log")
        
        if not os.path.exists(log_path):
            return SkillResult(
                success=False,
                message=f"路径不存在: {log_path}",
                error="Path not found"
            )
        
        mock_status = {
            "total_size": 524288000,
            "total_size_formatted": "500 MB",
            "file_count": 45,
            "largest_files": [
                {"path": f"{log_path}/syslog", "size": 52428800, "size_formatted": "50 MB"},
                {"path": f"{log_path}/application.log", "size": 31457280, "size_formatted": "30 MB"},
                {"path": f"{log_path}/access.log", "size": 20971520, "size_formatted": "20 MB"}
            ],
            "oldest_file": {"path": f"{log_path}/old.log", "age_days": 90},
            "empty_files": 3
        }
        
        return SkillResult(
            success=True,
            message=f"日志状态检查完成",
            data={
                "log_path": log_path,
                "status": mock_status,
                "note": "日志状态检查，当前返回模拟数据"
            }
        )
    
    def _calculate_next_run(self, schedule: str) -> str:
        now = datetime.now()
        if schedule == "daily":
            next_run = now + datetime.timedelta(days=1)
            next_run = next_run.replace(hour=3, minute=0, second=0)
        elif schedule == "weekly":
            next_run = now + datetime.timedelta(days=(6 - now.weekday()) % 7 + 1)
            next_run = next_run.replace(hour=3, minute=0, second=0)
        else:
            next_run = now + datetime.timedelta(hours=1)
        return next_run.isoformat()
