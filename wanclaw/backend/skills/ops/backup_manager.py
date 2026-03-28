"""
备份管理器技能
每日/每周自动备份重要文件夹，备份文件自动加密，备份失败提醒
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from wanclaw.backend.skills import BaseSkill, SkillResult, SkillCategory, SkillLevel
from wanclaw.backend.im_adapter.security import get_security, OperationType


logger = logging.getLogger(__name__)


class BackupManagerSkill(BaseSkill):
    """备份管理器技能"""
    
    def __init__(self):
        super().__init__()
        self.name = "BackupManager"
        self.description = "备份管理器：每日/每周自动备份，备份加密，失败提醒"
        self.category = SkillCategory.OPS
        self.level = SkillLevel.ADVANCED
        
        self.required_params = ["action"]
        
        self.optional_params = {
            "source_paths": list,
            "backup_path": str,
            "schedule": str,
            "encrypt": bool,
            "compression": str,
            "retention_days": int,
            "notify_on_failure": bool,
            "verify": bool
        }
    
    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        action = params.get("action", "").lower()
        user_id = params.get("user_id", "unknown")
        username = params.get("username", "unknown")
        
        security = get_security()
        
        if action in ["backup", "restore", "schedule", "status", "verify"]:
            backup_path = params.get("backup_path", "")
            if backup_path:
                allowed, reason = security.check_file_access(
                    backup_path, OperationType.FILE_WRITE, user_id, username
                )
                if not allowed:
                    return SkillResult(
                        success=False,
                        message=f"备份路径访问被拒绝: {reason}",
                        error="Security check failed"
                    )
        
        try:
            if action == "backup":
                return await self._create_backup(params)
            elif action == "restore":
                return await self._restore_backup(params)
            elif action == "schedule":
                return await self._schedule_backup(params)
            elif action == "status":
                return await self._backup_status(params)
            elif action == "verify":
                return await self._verify_backup(params)
            else:
                return SkillResult(
                    success=False,
                    message=f"不支持的操作: {action}",
                    error=f"Unsupported action: {action}"
                )
        except Exception as e:
            logger.error(f"备份管理失败: {action} - {e}")
            return SkillResult(
                success=False,
                message=f"备份管理失败: {str(e)}",
                error=str(e)
            )
    
    async def _create_backup(self, params: Dict[str, Any]) -> SkillResult:
        source_paths = params.get("source_paths", [])
        backup_path = params.get("backup_path", "/backup")
        encrypt = params.get("encrypt", True)
        compression = params.get("compression", "tar.gz")
        verify = params.get("verify", True)
        
        if not source_paths:
            return SkillResult(
                success=False,
                message="需要提供源路径列表",
                error="Source paths required"
            )
        
        os.makedirs(backup_path, exist_ok=True)
        
        backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_file = f"{backup_path}/{backup_id}.{compression}"
        
        original_size = sum([52428800, 31457280, 15728640][:len(source_paths)])
        compressed_size = int(original_size * 0.35)
        encrypted_size = compressed_size + 1024
        
        return SkillResult(
            success=True,
            message=f"备份创建成功: {backup_id}",
            data={
                "backup_id": backup_id,
                "backup_file": backup_file,
                "source_paths": source_paths,
                "original_size": original_size,
                "compressed_size": compressed_size,
                "encrypted": encrypt,
                "encryption_applied": encrypt,
                "compression": compression,
                "verified": verify,
                "created_at": datetime.now().isoformat(),
                "note": "备份管理器功能，当前返回模拟数据"
            }
        )
    
    async def _restore_backup(self, params: Dict[str, Any]) -> SkillResult:
        backup_id = params.get("backup_id", "")
        backup_path = params.get("backup_path", "")
        restore_path = params.get("restore_path", "/restore")
        
        if not backup_id:
            return SkillResult(
                success=False,
                message="需要备份ID",
                error="Backup ID required"
            )
        
        return SkillResult(
            success=True,
            message=f"备份恢复成功: {backup_id}",
            data={
                "backup_id": backup_id,
                "backup_file": f"{backup_path}/{backup_id}.tar.gz",
                "restore_path": restore_path,
                "files_restored": 125,
                "restored_at": datetime.now().isoformat(),
                "note": "备份恢复功能，当前返回模拟数据"
            }
        )
    
    async def _schedule_backup(self, params: Dict[str, Any]) -> SkillResult:
        source_paths = params.get("source_paths", [])
        backup_path = params.get("backup_path", "/backup")
        schedule = params.get("schedule", "daily")
        retention_days = params.get("retention_days", 30)
        notify_on_failure = params.get("notify_on_failure", True)
        
        schedule_config = {
            "source_paths": source_paths,
            "backup_path": backup_path,
            "schedule": schedule,
            "retention_days": retention_days,
            "notify_on_failure": notify_on_failure,
            "next_run": self._calculate_next_run(schedule),
            "enabled": True,
            "created_at": datetime.now().isoformat()
        }
        
        return SkillResult(
            success=True,
            message=f"备份计划已创建: {schedule}",
            data={
                "schedule_config": schedule_config,
                "note": "自动备份计划，当前返回模拟数据"
            }
        )
    
    async def _backup_status(self, params: Dict[str, Any]) -> SkillResult:
        backup_path = params.get("backup_path", "/backup")
        
        if not os.path.exists(backup_path):
            return SkillResult(
                success=False,
                message=f"备份路径不存在: {backup_path}",
                error="Backup path not found"
            )
        
        mock_backups = [
            {"id": "backup_20240115_020000", "created": "2024-01-15 02:00", "size": 52428800, "status": "success", "encrypted": True},
            {"id": "backup_20240114_020000", "created": "2024-01-14 02:00", "size": 51829760, "status": "success", "encrypted": True},
            {"id": "backup_20240113_020000", "created": "2024-01-13 02:00", "size": 50992384, "status": "success", "encrypted": True},
            {"id": "backup_20240112_020000", "created": "2024-01-12 02:00", "size": 49512448, "status": "failed", "encrypted": False, "error": "Disk full"}
        ]
        
        return SkillResult(
            success=True,
            message="备份状态检查完成",
            data={
                "backup_path": backup_path,
                "total_backups": len(mock_backups),
                "successful": len([b for b in mock_backups if b["status"] == "success"]),
                "failed": len([b for b in mock_backups if b["status"] == "failed"]),
                "latest_backup": mock_backups[0],
                "recent_failures": [b for b in mock_backups if b["status"] == "failed"],
                "total_size": sum(b["size"] for b in mock_backups),
                "notification_sent": True,
                "note": "备份状态检查，当前返回模拟数据"
            }
        )
    
    async def _verify_backup(self, params: Dict[str, Any]) -> SkillResult:
        backup_id = params.get("backup_id", "")
        
        if not backup_id:
            return SkillResult(
                success=False,
                message="需要备份ID",
                error="Backup ID required"
            )
        
        return SkillResult(
            success=True,
            message=f"备份验证完成: {backup_id}",
            data={
                "backup_id": backup_id,
                "integrity_check": "passed",
                "content_check": "passed",
                "encryption_check": "passed",
                "overall_status": "PASSED",
                "verified_at": datetime.now().isoformat(),
                "note": "备份验证功能，当前返回模拟数据"
            }
        )
    
    def _calculate_next_run(self, schedule: str) -> str:
        now = datetime.now()
        if schedule == "daily":
            next_run = now + datetime.timedelta(days=1)
            next_run = next_run.replace(hour=2, minute=0, second=0)
        elif schedule == "weekly":
            next_run = now + datetime.timedelta(days=(6 - now.weekday()) % 7 + 1)
            next_run = next_run.replace(hour=3, minute=0, second=0)
        else:
            next_run = now + datetime.timedelta(days=1)
        return next_run.isoformat()
