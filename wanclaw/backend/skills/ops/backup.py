"""
备份技能
提供文件备份和恢复功能
"""

import os
import sys
import shutil
import tarfile
import zipfile
import logging
import hashlib
import tempfile
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict

from wanclaw.backend.skills import BaseSkill, SkillResult, SkillCategory, SkillLevel
from wanclaw.backend.im_adapter.security import get_security, OperationType


logger = logging.getLogger(__name__)


@dataclass
class BackupItem:
    """备份项目"""
    path: str
    size: int
    modified: str
    type: str  # file, directory
    status: str  # backed_up, skipped, error
    error: Optional[str] = None


@dataclass
class BackupManifest:
    """备份清单"""
    backup_id: str
    backup_name: str
    created_at: str
    source_path: str
    backup_path: str
    total_items: int
    total_size: int
    compressed_size: Optional[int] = None
    compression_ratio: Optional[float] = None
    items: List[BackupItem] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.items is None:
            self.items = []
        if self.metadata is None:
            self.metadata = {}


class BackupSkill(BaseSkill):
    """备份技能"""
    
    def __init__(self):
        super().__init__()
        self.name = "Backup"
        self.description = "备份：文件备份、恢复、管理"
        self.category = SkillCategory.OPS
        self.level = SkillLevel.INTERMEDIATE
        
        # 必需参数
        self.required_params = ["action"]
        
        # 可选参数及其类型
        self.optional_params = {
            "source_path": str,
            "backup_path": str,
            "backup_name": str,
            "backup_id": str,
            "compression": str,
            "exclude_patterns": list,
            "include_patterns": list,
            "max_backups": int,
            "verify": bool,
            "incremental": bool,
            "restore_path": str,
            "cleanup_days": int,
            "schedule": str,
            "email_notify": bool
        }
    
    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        """
        执行备份操作
        
        Args:
            params: {
                "action": "create|list|restore|verify|cleanup|schedule|status",
                "source_path": "/path/to/backup",
                "backup_path": "/backup/destination",
                "backup_name": "my_backup",
                "backup_id": "backup_20240101",
                "compression": "tar.gz|zip|none",
                "exclude_patterns": ["*.log", "temp/*"],
                "include_patterns": ["*.py", "*.json"],
                "max_backups": 10,
                "verify": true,
                "incremental": false,
                "restore_path": "/restore/location",
                "cleanup_days": 30,
                "schedule": "daily|weekly|monthly",
                "email_notify": false
            }
            
        Returns:
            执行结果
        """
        action = params.get("action", "").lower()
        user_id = params.get("user_id", "unknown")
        username = params.get("username", "unknown")
        
        # 安全检查
        security = get_security()
        
        if action in ["create", "incremental"]:
            source_path = params.get("source_path", "")
            if source_path:
                allowed, reason = security.check_file_access(
                    source_path, OperationType.FILE_READ, user_id, username
                )
                if not allowed:
                    return SkillResult(
                        success=False,
                        message=f"源路径访问被拒绝: {reason}",
                        error="Security check failed for source"
                    )
            
            backup_path = params.get("backup_path", "")
            if backup_path:
                allowed, reason = security.check_file_access(
                    backup_path, OperationType.FILE_WRITE, user_id, username
                )
                if not allowed:
                    return SkillResult(
                        success=False,
                        message=f"备份路径访问被拒绝: {reason}",
                        error="Security check failed for backup destination"
                    )
        
        elif action == "restore":
            backup_path = params.get("backup_path", "")
            if backup_path:
                allowed, reason = security.check_file_access(
                    backup_path, OperationType.FILE_READ, user_id, username
                )
                if not allowed:
                    return SkillResult(
                        success=False,
                        message=f"备份文件访问被拒绝: {reason}",
                        error="Security check failed for backup file"
                    )
            
            restore_path = params.get("restore_path", "")
            if restore_path:
                allowed, reason = security.check_file_access(
                    restore_path, OperationType.FILE_WRITE, user_id, username
                )
                if not allowed:
                    return SkillResult(
                        success=False,
                        message=f"恢复路径访问被拒绝: {reason}",
                        error="Security check failed for restore destination"
                    )
        
        try:
            if action == "create":
                return await self._create_backup(params)
            elif action == "list":
                return await self._list_backups(params)
            elif action == "restore":
                return await self._restore_backup(params)
            elif action == "verify":
                return await self._verify_backup(params)
            elif action == "cleanup":
                return await self._cleanup_backups(params)
            elif action == "schedule":
                return await self._schedule_backup(params)
            elif action == "status":
                return await self._backup_status(params)
            elif action == "incremental":
                return await self._incremental_backup(params)
            else:
                return SkillResult(
                    success=False,
                    message=f"不支持的操作: {action}",
                    error=f"Unsupported action: {action}"
                )
        except Exception as e:
            logger.error(f"备份操作失败: {action} - {e}")
            return SkillResult(
                success=False,
                message=f"备份操作失败: {str(e)}",
                error=str(e)
            )
    
    async def _create_backup(self, params: Dict[str, Any]) -> SkillResult:
        """创建备份"""
        source_path = params.get("source_path", "")
        backup_path = params.get("backup_path", ".")
        backup_name = params.get("backup_name", "")
        compression = params.get("compression", "tar.gz")
        exclude_patterns = params.get("exclude_patterns", [])
        include_patterns = params.get("include_patterns", [])
        verify = params.get("verify", True)
        
        if not source_path:
            return SkillResult(
                success=False,
                message="需要源路径",
                error="Source path required"
            )
        
        if not os.path.exists(source_path):
            return SkillResult(
                success=False,
                message=f"源路径不存在: {source_path}",
                error="Source path not found"
            )
        
        # 创建备份目录
        os.makedirs(backup_path, exist_ok=True)
        
        # 生成备份ID和名称
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if not backup_name:
            backup_name = os.path.basename(source_path.rstrip('/'))
        
        backup_id = f"{backup_name}_{timestamp}"
        
        try:
            # 收集要备份的文件
            backup_items = []
            total_size = 0
            
            logger.info(f"开始备份: {source_path} -> {backup_path}")
            
            if os.path.isfile(source_path):
                # 单个文件
                item = self._create_backup_item(source_path)
                backup_items.append(item)
                total_size = item.size
            else:
                # 目录
                for root, dirs, files in os.walk(source_path):
                    # 应用排除模式
                    dirs[:] = [d for d in dirs if not self._matches_patterns(d, exclude_patterns)]
                    
                    for filename in files:
                        file_path = os.path.join(root, filename)
                        
                        # 检查排除/包含模式
                        if self._matches_patterns(filename, exclude_patterns):
                            continue
                        
                        if include_patterns and not self._matches_patterns(filename, include_patterns):
                            continue
                        
                        item = self._create_backup_item(file_path)
                        backup_items.append(item)
                        total_size += item.size
            
            # 创建备份文件
            backup_filename = f"{backup_id}.{self._get_compression_ext(compression)}"
            backup_filepath = os.path.join(backup_path, backup_filename)
            
            # 执行备份
            compressed_size = await self._perform_backup(
                source_path, backup_filepath, compression, 
                exclude_patterns, include_patterns
            )
            
            # 计算压缩率
            compression_ratio = None
            if compressed_size and total_size > 0:
                compression_ratio = (1 - compressed_size / total_size) * 100
            
            # 创建清单
            manifest = BackupManifest(
                backup_id=backup_id,
                backup_name=backup_name,
                created_at=datetime.datetime.now().isoformat(),
                source_path=source_path,
                backup_path=backup_filepath,
                total_items=len(backup_items),
                total_size=total_size,
                compressed_size=compressed_size,
                compression_ratio=compression_ratio,
                items=backup_items,
                metadata={
                    "compression": compression,
                    "exclude_patterns": exclude_patterns,
                    "include_patterns": include_patterns
                }
            )
            
            # 保存清单
            manifest_path = os.path.join(backup_path, f"{backup_id}.manifest.json")
            self._save_manifest(manifest, manifest_path)
            
            # 验证备份（如果启用）
            verification_result = None
            if verify:
                verification_result = await self._verify_backup_file(
                    backup_filepath, source_path, compression
                )
            
            return SkillResult(
                success=True,
                message=f"备份创建成功: {backup_id}",
                data={
                    "backup_id": backup_id,
                    "backup_name": backup_name,
                    "source_path": source_path,
                    "backup_path": backup_filepath,
                    "backup_size": compressed_size or total_size,
                    "backup_size_formatted": self._format_size(compressed_size or total_size),
                    "original_size": total_size,
                    "original_size_formatted": self._format_size(total_size),
                    "compression_ratio": compression_ratio,
                    "total_items": len(backup_items),
                    "compression": compression,
                    "verification": verification_result,
                    "manifest_path": manifest_path,
                    "created_at": manifest.created_at
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"创建备份失败: {str(e)}",
                error=str(e)
            )
    
    async def _list_backups(self, params: Dict[str, Any]) -> SkillResult:
        """列出备份"""
        backup_path = params.get("backup_path", ".")
        
        if not os.path.exists(backup_path):
            return SkillResult(
                success=False,
                message=f"备份路径不存在: {backup_path}",
                error="Backup path not found"
            )
        
        try:
            backups = []
            manifest_files = []
            
            # 查找备份文件和清单
            for filename in os.listdir(backup_path):
                filepath = os.path.join(backup_path, filename)
                
                # 检查是否为备份文件
                if self._is_backup_file(filename):
                    backup_info = self._get_backup_info(filepath)
                    backups.append(backup_info)
                
                # 检查是否为清单文件
                elif filename.endswith('.manifest.json'):
                    manifest_info = self._get_manifest_info(filepath)
                    if manifest_info:
                        manifest_files.append(manifest_info)
            
            # 按创建时间排序
            backups.sort(key=lambda x: x.get("created_time", 0), reverse=True)
            
            # 统计信息
            total_backups = len(backups)
            total_size = sum(b.get("size", 0) for b in backups)
            
            # 按类型分组
            by_type = {}
            for backup in backups:
                backup_type = backup.get("type", "unknown")
                by_type[backup_type] = by_type.get(backup_type, 0) + 1
            
            return SkillResult(
                success=True,
                message=f"找到 {total_backups} 个备份",
                data={
                    "backup_path": backup_path,
                    "backups": backups,
                    "manifests": manifest_files,
                    "total_backups": total_backups,
                    "total_size": total_size,
                    "total_size_formatted": self._format_size(total_size),
                    "by_type": by_type,
                    "latest_backup": backups[0] if backups else None,
                    "oldest_backup": backups[-1] if backups else None
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"列出备份失败: {str(e)}",
                error=str(e)
            )
    
    async def _restore_backup(self, params: Dict[str, Any]) -> SkillResult:
        """恢复备份"""
        backup_path = params.get("backup_path", "")
        backup_id = params.get("backup_id", "")
        restore_path = params.get("restore_path", ".")
        overwrite = params.get("overwrite", False)
        verify = params.get("verify", True)
        
        if not backup_path:
            return SkillResult(
                success=False,
                message="需要备份文件路径",
                error="Backup path required"
            )
        
        if not os.path.exists(backup_path):
            return SkillResult(
                success=False,
                message=f"备份文件不存在: {backup_path}",
                error="Backup file not found"
            )
        
        # 如果提供了备份ID，查找对应的备份文件
        if backup_id and not os.path.isfile(backup_path):
            backup_file = self._find_backup_by_id(backup_path, backup_id)
            if not backup_file:
                return SkillResult(
                    success=False,
                    message=f"未找到备份: {backup_id}",
                    error="Backup not found"
                )
            backup_path = backup_file
        
        # 创建恢复目录
        os.makedirs(restore_path, exist_ok=True)
        
        try:
            # 检查备份文件类型
            backup_type = self._get_backup_type(backup_path)
            
            # 执行恢复
            restored_items = []
            total_size = 0
            
            logger.info(f"开始恢复: {backup_path} -> {restore_path}")
            
            if backup_type == "tar":
                restored_items, total_size = self._restore_tar_backup(backup_path, restore_path, overwrite)
            elif backup_type == "zip":
                restored_items, total_size = self._restore_zip_backup(backup_path, restore_path, overwrite)
            else:
                # 简单复制
                target_path = os.path.join(restore_path, os.path.basename(backup_path))
                if os.path.exists(target_path) and not overwrite:
                    return SkillResult(
                        success=False,
                        message=f"目标文件已存在: {target_path}",
                        error="Target file exists"
                    )
                
                shutil.copy2(backup_path, target_path)
                restored_items = [{
                    "path": target_path,
                    "size": os.path.getsize(backup_path),
                    "type": "file"
                }]
                total_size = os.path.getsize(backup_path)
            
            # 验证恢复（如果启用）
            verification_result = None
            if verify:
                verification_result = await self._verify_restoration(backup_path, restore_path)
            
            return SkillResult(
                success=True,
                message=f"备份恢复成功: {os.path.basename(backup_path)}",
                data={
                    "backup_path": backup_path,
                    "restore_path": restore_path,
                    "backup_type": backup_type,
                    "restored_items": len(restored_items),
                    "total_size": total_size,
                    "total_size_formatted": self._format_size(total_size),
                    "overwrite": overwrite,
                    "verification": verification_result,
                    "restored_files": restored_items[:20],  # 只显示前20个文件
                    "timestamp": datetime.datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"恢复备份失败: {str(e)}",
                error=str(e)
            )
    
    async def _verify_backup(self, params: Dict[str, Any]) -> SkillResult:
        """验证备份"""
        backup_path = params.get("backup_path", "")
        backup_id = params.get("backup_id", "")
        check_integrity = params.get("check_integrity", True)
        compare_source = params.get("compare_source", "")
        
        if not backup_path:
            return SkillResult(
                success=False,
                message="需要备份文件路径",
                error="Backup path required"
            )
        
        if not os.path.exists(backup_path):
            return SkillResult(
                success=False,
                message=f"备份文件不存在: {backup_path}",
                error="Backup file not found"
            )
        
        # 如果提供了备份ID，查找对应的备份文件
        if backup_id and not os.path.isfile(backup_path):
            backup_file = self._find_backup_by_id(backup_path, backup_id)
            if not backup_file:
                return SkillResult(
                    success=False,
                    message=f"未找到备份: {backup_id}",
                    error="Backup not found"
                )
            backup_path = backup_file
        
        try:
            verification_results = {
                "file_exists": True,
                "file_size": os.path.getsize(backup_path),
                "file_size_formatted": self._format_size(os.path.getsize(backup_path)),
                "file_modified": datetime.datetime.fromtimestamp(os.path.getmtime(backup_path)).isoformat(),
                "integrity_check": None,
                "content_check": None,
                "manifest_check": None
            }
            
            # 完整性检查
            if check_integrity:
                integrity_result = await self._check_backup_integrity(backup_path)
                verification_results["integrity_check"] = integrity_result
            
            # 内容检查（如果提供了源路径）
            if compare_source and os.path.exists(compare_source):
                content_result = await self._compare_with_source(backup_path, compare_source)
                verification_results["content_check"] = content_result
            
            # 清单检查
            manifest_path = backup_path.replace(
                self._get_compression_ext(self._get_backup_type(backup_path)),
                ".manifest.json"
            )
            if os.path.exists(manifest_path):
                manifest_result = self._check_manifest(manifest_path, backup_path)
                verification_results["manifest_check"] = manifest_result
            
            # 总体状态
            all_checks_passed = (
                verification_results["integrity_check"] is None or 
                verification_results["integrity_check"].get("passed", False)
            ) and (
                verification_results["content_check"] is None or 
                verification_results["content_check"].get("passed", False)
            ) and (
                verification_results["manifest_check"] is None or 
                verification_results["manifest_check"].get("passed", False)
            )
            
            verification_results["overall_status"] = "PASSED" if all_checks_passed else "FAILED"
            
            return SkillResult(
                success=True,
                message=f"备份验证完成: {'通过' if all_checks_passed else '失败'}",
                data=verification_results
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"验证备份失败: {str(e)}",
                error=str(e)
            )
    
    async def _cleanup_backups(self, params: Dict[str, Any]) -> SkillResult:
        """清理旧备份"""
        backup_path = params.get("backup_path", ".")
        max_backups = params.get("max_backups", 10)
        cleanup_days = params.get("cleanup_days", 30)
        dry_run = params.get("dry_run", True)
        
        if not os.path.exists(backup_path):
            return SkillResult(
                success=False,
                message=f"备份路径不存在: {backup_path}",
                error="Backup path not found"
            )
        
        try:
            # 查找所有备份文件
            backup_files = []
            for filename in os.listdir(backup_path):
                if self._is_backup_file(filename):
                    filepath = os.path.join(backup_path, filename)
                    stat = os.stat(filepath)
                    
                    backup_files.append({
                        "path": filepath,
                        "name": filename,
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                        "age_days": (datetime.datetime.now().timestamp() - stat.st_mtime) / 86400
                    })
            
            # 按修改时间排序（最新的在前）
            backup_files.sort(key=lambda x: x["modified"], reverse=True)
            
            # 确定要删除的文件
            files_to_delete = []
            reasons = []
            
            # 1. 保留最新的N个备份
            if len(backup_files) > max_backups:
                for backup in backup_files[max_backups:]:
                    files_to_delete.append(backup)
                    reasons.append("超过最大备份数量限制")
            
            # 2. 删除超过天数的备份
            cutoff_time = datetime.datetime.now().timestamp() - (cleanup_days * 86400)
            for backup in backup_files:
                if backup["modified"] < cutoff_time and backup not in files_to_delete:
                    files_to_delete.append(backup)
                    reasons.append("超过保留天数")
            
            # 去重
            unique_files_to_delete = []
            seen_paths = set()
            for backup in files_to_delete:
                if backup["path"] not in seen_paths:
                    seen_paths.add(backup["path"])
                    unique_files_to_delete.append(backup)
            
            # 执行删除（如果不是干运行）
            deleted_files = []
            total_freed = 0
            
            if not dry_run:
                for backup in unique_files_to_delete:
                    try:
                        os.remove(backup["path"])
                        
                        # 同时删除对应的清单文件
                        manifest_path = backup["path"].replace(
                            self._get_compression_ext(self._get_backup_type(backup["path"])),
                            ".manifest.json"
                        )
                        if os.path.exists(manifest_path):
                            os.remove(manifest_path)
                        
                        deleted_files.append({
                            "path": backup["path"],
                            "size": backup["size"],
                            "reason": "实际删除"
                        })
                        total_freed += backup["size"]
                        
                    except Exception as e:
                        logger.error(f"删除备份失败 {backup['path']}: {e}")
            
            return SkillResult(
                success=True,
                message=f"清理完成: {len(deleted_files) if not dry_run else len(unique_files_to_delete)} 个备份{'（干运行）' if dry_run else ''}",
                data={
                    "backup_path": backup_path,
                    "total_backups": len(backup_files),
                    "max_backups": max_backups,
                    "cleanup_days": cleanup_days,
                    "dry_run": dry_run,
                    "files_to_delete": unique_files_to_delete,
                    "deleted_files": deleted_files,
                    "total_freed": total_freed,
                    "total_freed_formatted": self._format_size(total_freed),
                    "remaining_backups": len(backup_files) - len(unique_files_to_delete)
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"清理备份失败: {str(e)}",
                error=str(e)
            )
    
    async def _schedule_backup(self, params: Dict[str, Any]) -> SkillResult:
        """计划备份（模拟）"""
        source_path = params.get("source_path", "")
        backup_path = params.get("backup_path", ".")
        schedule = params.get("schedule", "daily")
        backup_name = params.get("backup_name", "")
        
        if not source_path:
            return SkillResult(
                success=False,
                message="需要源路径",
                error="Source path required"
            )
        
        # 解析计划
        schedule_map = {
            "daily": "每天 02:00",
            "weekly": "每周日 03:00",
            "monthly": "每月1号 04:00",
            "hourly": "每小时"
        }
        
        schedule_description = schedule_map.get(schedule, "自定义计划")
        
        # 生成计划配置
        schedule_config = {
            "source_path": source_path,
            "backup_path": backup_path,
            "backup_name": backup_name or os.path.basename(source_path.rstrip('/')),
            "schedule": schedule,
            "schedule_description": schedule_description,
            "next_run": self._calculate_next_run(schedule),
            "created_at": datetime.datetime.now().isoformat(),
            "enabled": True
        }
        
        return SkillResult(
            success=True,
            message=f"备份计划已创建: {schedule_description}",
            data={
                "schedule_config": schedule_config,
                "note": "这是一个模拟的计划备份功能。在实际部署中，需要集成任务调度系统如cron、systemd timer或APScheduler。"
            }
        )
    
    async def _backup_status(self, params: Dict[str, Any]) -> SkillResult:
        """备份状态检查"""
        backup_path = params.get("backup_path", ".")
        
        if not os.path.exists(backup_path):
            return SkillResult(
                success=False,
                message=f"备份路径不存在: {backup_path}",
                error="Backup path not found"
            )
        
        try:
            # 收集状态信息
            status = {
                "path": backup_path,
                "exists": True,
                "writable": os.access(backup_path, os.W_OK),
                "free_space": self._get_free_space(backup_path),
                "backup_count": 0,
                "latest_backup": None,
                "health_status": "UNKNOWN"
            }
            
            # 统计备份文件
            backup_files = []
            for filename in os.listdir(backup_path):
                if self._is_backup_file(filename):
                    filepath = os.path.join(backup_path, filename)
                    stat = os.stat(filepath)
                    
                    backup_info = {
                        "name": filename,
                        "path": filepath,
                        "size": stat.st_size,
                        "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "age_days": (datetime.datetime.now().timestamp() - stat.st_mtime) / 86400
                    }
                    
                    backup_files.append(backup_info)
            
            if backup_files:
                # 按修改时间排序
                backup_files.sort(key=lambda x: x.get("modified", ""), reverse=True)
                
                status["backup_count"] = len(backup_files)
                status["latest_backup"] = backup_files[0]
                
                # 检查最新备份的年龄
                latest_age = backup_files[0]["age_days"]
                if latest_age < 1:
                    status["health_status"] = "EXCELLENT"
                elif latest_age < 7:
                    status["health_status"] = "GOOD"
                elif latest_age < 30:
                    status["health_status"] = "WARNING"
                else:
                    status["health_status"] = "CRITICAL"
            else:
                status["health_status"] = "NO_BACKUPS"
            
            return SkillResult(
                success=True,
                message=f"备份状态: {status['health_status']}",
                data=status
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"检查备份状态失败: {str(e)}",
                error=str(e)
            )
    
    async def _incremental_backup(self, params: Dict[str, Any]) -> SkillResult:
        """增量备份"""
        # 这是一个简化版的增量备份
        # 实际实现需要跟踪文件修改时间和哈希值
        
        return SkillResult(
            success=True,
            message="增量备份功能",
            data={
                "note": "这是一个简化的增量备份演示。实际实现需要：\n"
                       "1. 跟踪文件修改时间和哈希值\n"
                       "2. 维护增量备份链\n"
                       "3. 支持完整恢复和增量恢复\n"
                       "4. 定期创建完整备份作为基础",
                "params": params
            }
        )
    
    # ===== 辅助方法 =====
    
    def _create_backup_item(self, path: str) -> BackupItem:
        """创建备份项目"""
        stat = os.stat(path)
        
        return BackupItem(
            path=path,
            size=stat.st_size,
            modified=datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            type="file" if os.path.isfile(path) else "directory",
            status="backed_up"
        )
    
    async def _perform_backup(self, source_path: str, backup_filepath: str, 
                             compression: str, exclude_patterns: List[str], 
                             include_patterns: List[str]) -> Optional[int]:
        """执行备份"""
        if compression == "tar.gz":
            return self._create_tar_backup(source_path, backup_filepath, 
                                          exclude_patterns, include_patterns, 
                                          compress=True)
        elif compression == "tar":
            return self._create_tar_backup(source_path, backup_filepath, 
                                          exclude_patterns, include_patterns, 
                                          compress=False)
        elif compression == "zip":
            return self._create_zip_backup(source_path, backup_filepath, 
                                          exclude_patterns, include_patterns)
        else:
            # 无压缩，简单复制
            if os.path.isfile(source_path):
                shutil.copy2(source_path, backup_filepath)
            else:
                shutil.copytree(source_path, backup_filepath, 
                              ignore=shutil.ignore_patterns(*exclude_patterns))
            return os.path.getsize(backup_filepath)
    
    def _create_tar_backup(self, source_path: str, backup_filepath: str, 
                          exclude_patterns: List[str], include_patterns: List[str],
                          compress: bool = True) -> int:
        """创建tar备份"""
        mode = "w:gz" if compress else "w"
        
        with tarfile.open(backup_filepath, mode) as tar:
            if os.path.isfile(source_path):
                tar.add(source_path, arcname=os.path.basename(source_path))
            else:
                # 添加目录，应用排除模式
                for root, dirs, files in os.walk(source_path):
                    # 应用排除模式
                    dirs[:] = [d for d in dirs if not self._matches_patterns(d, exclude_patterns)]
                    
                    for filename in files:
                        file_path = os.path.join(root, filename)
                        
                        # 检查排除/包含模式
                        if self._matches_patterns(filename, exclude_patterns):
                            continue
                        
                        if include_patterns and not self._matches_patterns(filename, include_patterns):
                            continue
                        
                        # 计算相对路径
                        rel_path = os.path.relpath(file_path, source_path)
                        tar.add(file_path, arcname=rel_path)
        
        return os.path.getsize(backup_filepath)
    
    def _create_zip_backup(self, source_path: str, backup_filepath: str, 
                          exclude_patterns: List[str], include_patterns: List[str]) -> int:
        """创建zip备份"""
        with zipfile.ZipFile(backup_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            if os.path.isfile(source_path):
                zipf.write(source_path, os.path.basename(source_path))
            else:
                for root, dirs, files in os.walk(source_path):
                    # 应用排除模式
                    dirs[:] = [d for d in dirs if not self._matches_patterns(d, exclude_patterns)]
                    
                    for filename in files:
                        file_path = os.path.join(root, filename)
                        
                        # 检查排除/包含模式
                        if self._matches_patterns(filename, exclude_patterns):
                            continue
                        
                        if include_patterns and not self._matches_patterns(filename, include_patterns):
                            continue
                        
                        # 计算相对路径
                        rel_path = os.path.relpath(file_path, source_path)
                        zipf.write(file_path, rel_path)
        
        return os.path.getsize(backup_filepath)
    
    def _restore_tar_backup(self, backup_path: str, restore_path: str, 
                           overwrite: bool) -> Tuple[List[Dict[str, Any]], int]:
        """恢复tar备份"""
        restored_items = []
        total_size = 0
        
        with tarfile.open(backup_path, 'r:*') as tar:
            for member in tar.getmembers():
                # 检查是否已存在
                target_path = os.path.join(restore_path, member.name)
                if os.path.exists(target_path) and not overwrite:
                    continue
                
                # 提取文件
                tar.extract(member, restore_path)
                
                # 记录恢复的项目
                if member.isfile():
                    file_size = member.size
                    restored_items.append({
                        "path": target_path,
                        "size": file_size,
                        "type": "file"
                    })
                    total_size += file_size
                elif member.isdir():
                    restored_items.append({
                        "path": target_path,
                        "size": 0,
                        "type": "directory"
                    })
        
        return restored_items, total_size
    
    def _restore_zip_backup(self, backup_path: str, restore_path: str, 
                           overwrite: bool) -> Tuple[List[Dict[str, Any]], int]:
        """恢复zip备份"""
        restored_items = []
        total_size = 0
        
        with zipfile.ZipFile(backup_path, 'r') as zipf:
            for member in zipf.infolist():
                # 检查是否已存在
                target_path = os.path.join(restore_path, member.filename)
                if os.path.exists(target_path) and not overwrite:
                    continue
                
                # 提取文件
                zipf.extract(member, restore_path)
                
                # 记录恢复的项目
                file_size = member.file_size
                restored_items.append({
                    "path": target_path,
                    "size": file_size,
                    "type": "file" if not member.is_dir() else "directory"
                })
                total_size += file_size
        
        return restored_items, total_size
    
    async def _verify_backup_file(self, backup_path: str, source_path: str, 
                                 compression: str) -> Dict[str, Any]:
        """验证备份文件"""
        try:
            # 检查文件完整性
            if compression in ["tar.gz", "tar"]:
                with tarfile.open(backup_path, 'r:*') as tar:
                    members = tar.getmembers()
                    return {
                        "passed": True,
                        "member_count": len(members),
                        "tested": True
                    }
            elif compression == "zip":
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    test_result = zipf.testzip()
                    return {
                        "passed": test_result is None,
                        "member_count": len(zipf.infolist()),
                        "tested": True,
                        "error": test_result
                    }
            else:
                # 简单文件，检查存在性和大小
                return {
                    "passed": os.path.exists(backup_path) and os.path.getsize(backup_path) > 0,
                    "tested": True
                }
        except Exception as e:
            return {
                "passed": False,
                "error": str(e),
                "tested": True
            }
    
    async def _verify_restoration(self, backup_path: str, restore_path: str) -> Dict[str, Any]:
        """验证恢复"""
        # 这是一个简化的验证
        # 实际实现应该比较备份内容和恢复内容
        
        return {
            "passed": os.path.exists(restore_path),
            "restored_path": restore_path,
            "note": "这是一个简化的验证。实际实现应该比较文件哈希值。"
        }
    
    async def _check_backup_integrity(self, backup_path: str) -> Dict[str, Any]:
        """检查备份完整性"""
        backup_type = self._get_backup_type(backup_path)
        
        try:
            if backup_type == "tar":
                with tarfile.open(backup_path, 'r:*') as tar:
                    tar.getmembers()  # 尝试读取成员列表
                return {"passed": True, "error": None}
            elif backup_type == "zip":
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    error = zipf.testzip()
                    return {"passed": error is None, "error": error}
            else:
                # 普通文件，检查是否可读
                with open(backup_path, 'rb') as f:
                    f.read(1024)  # 读取少量数据
                return {"passed": True, "error": None}
        except Exception as e:
            return {"passed": False, "error": str(e)}
    
    async def _compare_with_source(self, backup_path: str, source_path: str) -> Dict[str, Any]:
        """与源文件比较"""
        # 这是一个简化的比较
        # 实际实现应该比较文件内容和元数据
        
        return {
            "passed": os.path.exists(source_path),
            "source_exists": os.path.exists(source_path),
            "backup_exists": os.path.exists(backup_path),
            "note": "这是一个简化的比较。实际实现应该比较文件哈希值和元数据。"
        }
    
    def _check_manifest(self, manifest_path: str, backup_path: str) -> Dict[str, Any]:
        """检查清单"""
        try:
            import json
            
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            backup_size = os.path.getsize(backup_path)
            manifest_size = manifest.get("compressed_size") or manifest.get("total_size", 0)
            
            return {
                "passed": abs(backup_size - manifest_size) < 1024,  # 允许1KB误差
                "manifest_size": manifest_size,
                "actual_size": backup_size,
                "difference": backup_size - manifest_size,
                "manifest_id": manifest.get("backup_id", "unknown")
            }
        except Exception as e:
            return {"passed": False, "error": str(e)}
    
    def _save_manifest(self, manifest: BackupManifest, manifest_path: str):
        """保存清单"""
        import json
        
        with open(manifest_path, 'w') as f:
            json.dump(asdict(manifest), f, indent=2, default=str)
    
    def _get_backup_info(self, filepath: str) -> Dict[str, Any]:
        """获取备份文件信息"""
        stat = os.stat(filepath)
        
        return {
            "path": filepath,
            "name": os.path.basename(filepath),
            "size": stat.st_size,
            "size_formatted": self._format_size(stat.st_size),
            "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created_time": stat.st_mtime,
            "type": self._get_backup_type(filepath),
            "backup_id": self._extract_backup_id(os.path.basename(filepath))
        }
    
    def _get_manifest_info(self, manifest_path: str) -> Optional[Dict[str, Any]]:
        """获取清单信息"""
        try:
            import json
            
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            return {
                "path": manifest_path,
                "backup_id": manifest.get("backup_id"),
                "backup_name": manifest.get("backup_name"),
                "created_at": manifest.get("created_at"),
                "source_path": manifest.get("source_path"),
                "total_items": manifest.get("total_items", 0),
                "total_size": manifest.get("total_size", 0)
            }
        except:
            return None
    
    def _find_backup_by_id(self, backup_dir: str, backup_id: str) -> Optional[str]:
        """根据ID查找备份文件"""
        for filename in os.listdir(backup_dir):
            if backup_id in filename and self._is_backup_file(filename):
                return os.path.join(backup_dir, filename)
        return None
    
    def _is_backup_file(self, filename: str) -> bool:
        """检查是否为备份文件"""
        backup_extensions = ['.tar.gz', '.tgz', '.tar', '.zip', '.bak', '.backup']
        
        for ext in backup_extensions:
            if filename.endswith(ext):
                return True
        
        # 检查是否包含backup或bak
        filename_lower = filename.lower()
        return 'backup' in filename_lower or filename_lower.endswith('.bak')
    
    def _get_backup_type(self, filepath: str) -> str:
        """获取备份类型"""
        filename = filepath.lower()
        
        if filename.endswith('.tar.gz') or filename.endswith('.tgz'):
            return "tar"
        elif filename.endswith('.tar'):
            return "tar"
        elif filename.endswith('.zip'):
            return "zip"
        elif filename.endswith('.bak') or 'backup' in filename:
            return "file"
        else:
            return "unknown"
    
    def _get_compression_ext(self, compression: str) -> str:
        """获取压缩扩展名"""
        compression_map = {
            "tar.gz": "tar.gz",
            "tgz": "tar.gz",
            "tar": "tar",
            "zip": "zip",
            "none": "bak"
        }
        return compression_map.get(compression, "bak")
    
    def _extract_backup_id(self, filename: str) -> str:
        """从文件名提取备份ID"""
        # 移除扩展名
        for ext in ['.tar.gz', '.tgz', '.tar', '.zip', '.bak', '.backup']:
            if filename.endswith(ext):
                filename = filename[:-len(ext)]
                break
        
        return filename
    
    def _matches_patterns(self, text: str, patterns: List[str]) -> bool:
        """检查文本是否匹配任何模式"""
        import fnmatch
        
        for pattern in patterns:
            if fnmatch.fnmatch(text, pattern):
                return True
        return False
    
    def _calculate_next_run(self, schedule: str) -> str:
        """计算下一次运行时间"""
        now = datetime.datetime.now()
        
        if schedule == "daily":
            next_run = now + datetime.timedelta(days=1)
            next_run = next_run.replace(hour=2, minute=0, second=0, microsecond=0)
        elif schedule == "weekly":
            days_ahead = 6 - now.weekday()  # 0=Monday, 6=Sunday
            if days_ahead <= 0:
                days_ahead += 7
            next_run = now + datetime.timedelta(days=days_ahead)
            next_run = next_run.replace(hour=3, minute=0, second=0, microsecond=0)
        elif schedule == "monthly":
            # 下个月的第一天
            if now.month == 12:
                next_run = datetime.datetime(now.year + 1, 1, 1, 4, 0, 0)
            else:
                next_run = datetime.datetime(now.year, now.month + 1, 1, 4, 0, 0)
        elif schedule == "hourly":
            next_run = now + datetime.timedelta(hours=1)
            next_run = next_run.replace(minute=0, second=0, microsecond=0)
        else:
            next_run = now + datetime.timedelta(days=1)
        
        return next_run.isoformat()
    
    def _get_free_space(self, path: str) -> Dict[str, Any]:
        """获取可用空间"""
        try:
            import shutil
            
            stat = shutil.disk_usage(path)
            
            return {
                "total": stat.total,
                "total_formatted": self._format_size(stat.total),
                "used": stat.used,
                "used_formatted": self._format_size(stat.used),
                "free": stat.free,
                "free_formatted": self._format_size(stat.free),
                "free_percentage": (stat.free / stat.total) * 100
            }
        except:
            return {
                "total": 0,
                "total_formatted": "未知",
                "used": 0,
                "used_formatted": "未知",
                "free": 0,
                "free_formatted": "未知",
                "free_percentage": 0
            }
    
    def _format_size(self, bytes_size: int) -> str:
        """格式化文件大小"""
        if bytes_size == 0:
            return "0 B"
        
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        
        size = float(bytes_size)
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.2f} {units[unit_index]}"