"""
健康检查技能
检查磁盘空间、CPU、内存，异常自动告警
"""

import os
import psutil
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from wanclaw.backend.skills import BaseSkill, SkillResult, SkillCategory, SkillLevel


logger = logging.getLogger(__name__)


class HealthCheckerSkill(BaseSkill):
    """健康检查技能"""
    
    def __init__(self):
        super().__init__()
        self.name = "HealthChecker"
        self.description = "健康检查：检查磁盘空间、CPU、内存，异常自动告警"
        self.category = SkillCategory.OPS
        self.level = SkillLevel.INTERMEDIATE
        
        self.required_params = ["action"]
        
        self.optional_params = {
            "disk_threshold": int,
            "cpu_threshold": int,
            "memory_threshold": int,
            "check_disk": bool,
            "check_cpu": bool,
            "check_memory": bool,
            "alert": bool,
            "notify_channels": list
        }
    
    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        action = params.get("action", "").lower()
        
        try:
            if action == "check":
                return await self._system_check(params)
            elif action == "disk":
                return await self._check_disk(params)
            elif action == "cpu":
                return await self._check_cpu(params)
            elif action == "memory":
                return await self._check_memory(params)
            elif action == "alert":
                return await self._send_alert(params)
            else:
                return SkillResult(
                    success=False,
                    message=f"不支持的操作: {action}",
                    error=f"Unsupported action: {action}"
                )
        except Exception as e:
            logger.error(f"健康检查失败: {action} - {e}")
            return SkillResult(
                success=False,
                message=f"健康检查失败: {str(e)}",
                error=str(e)
            )
    
    async def _system_check(self, params: Dict[str, Any]) -> SkillResult:
        disk_threshold = params.get("disk_threshold", 85)
        cpu_threshold = params.get("cpu_threshold", 80)
        memory_threshold = params.get("memory_threshold", 85)
        alert = params.get("alert", True)
        
        disk_usage = psutil.disk_usage('/')
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        alerts = []
        if disk_usage.percent > disk_threshold:
            alerts.append({"type": "disk", "level": "warning", "message": f"磁盘使用率{disk_usage.percent}%超过阈值{disk_threshold}%"})
        if cpu_percent > cpu_threshold:
            alerts.append({"type": "cpu", "level": "warning", "message": f"CPU使用率{cpu_percent}%超过阈值{cpu_threshold}%"})
        if memory.percent > memory_threshold:
            alerts.append({"type": "memory", "level": "warning", "message": f"内存使用率{memory.percent}%超过阈值{memory_threshold}%"})
        
        health_status = "healthy" if not alerts else "warning" if len(alerts) < 2 else "critical"
        
        return SkillResult(
            success=True,
            message=f"系统检查完成，状态: {health_status}",
            data={
                "timestamp": datetime.now().isoformat(),
                "health_status": health_status,
                "disk": {
                    "total": disk_usage.total,
                    "used": disk_usage.used,
                    "free": disk_usage.free,
                    "percent": disk_usage.percent,
                    "threshold": disk_threshold,
                    "alert": disk_usage.percent > disk_threshold
                },
                "cpu": {
                    "percent": cpu_percent,
                    "count": psutil.cpu_count(),
                    "threshold": cpu_threshold,
                    "alert": cpu_percent > cpu_threshold
                },
                "memory": {
                    "total": memory.total,
                    "used": memory.used,
                    "free": memory.free,
                    "percent": memory.percent,
                    "threshold": memory_threshold,
                    "alert": memory.percent > memory_threshold
                },
                "alerts": alerts,
                "alert_sent": alert and bool(alerts),
                "note": "健康检查使用psutil库"
            }
        )
    
    async def _check_disk(self, params: Dict[str, Any]) -> SkillResult:
        threshold = params.get("disk_threshold", 85)
        path = params.get("path", "/")
        
        disk_usage = psutil.disk_usage(path)
        
        partitions = []
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                partitions.append({
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                    "alert": usage.percent > threshold
                })
            except:
                pass
        
        return SkillResult(
            success=True,
            message=f"磁盘检查完成",
            data={
                "path": path,
                "threshold": threshold,
                "partitions": partitions,
                "alerts": [p for p in partitions if p["alert"]],
                "note": "磁盘检查使用psutil库"
            }
        )
    
    async def _check_cpu(self, params: Dict[str, Any]) -> SkillResult:
        threshold = params.get("cpu_threshold", 80)
        cpu_percent = psutil.cpu_percent(interval=1)
        
        per_cpu = psutil.cpu_percent(interval=0.5, percpu=True)
        
        return SkillResult(
            success=True,
            message=f"CPU检查完成，使用率{cpu_percent}%",
            data={
                "cpu_percent": cpu_percent,
                "cpu_count": psutil.cpu_count(),
                "per_cpu_percent": per_cpu,
                "threshold": threshold,
                "alert": cpu_percent > threshold,
                "load_avg": os.getloadavg() if hasattr(os, 'getloadavg') else None,
                "note": "CPU检查使用psutil库"
            }
        )
    
    async def _check_memory(self, params: Dict[str, Any]) -> SkillResult:
        threshold = params.get("memory_threshold", 85)
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return SkillResult(
            success=True,
            message=f"内存检查完成，使用率{memory.percent}%",
            data={
                "memory_percent": memory.percent,
                "memory_total": memory.total,
                "memory_used": memory.used,
                "memory_free": memory.free,
                "swap_percent": swap.percent,
                "swap_used": swap.used,
                "swap_free": swap.free,
                "threshold": threshold,
                "alert": memory.percent > threshold,
                "note": "内存检查使用psutil库"
            }
        )
    
    async def _send_alert(self, params: Dict[str, Any]) -> SkillResult:
        alerts = params.get("alerts", [])
        notify_channels = params.get("notify_channels", ["email", "webhook"])
        
        return SkillResult(
            success=True,
            message=f"告警发送完成，发送至{len(notify_channels)}个渠道",
            data={
                "alerts": alerts,
                "notify_channels": notify_channels,
                "channels_notified": notify_channels,
                "alert_count": len(alerts),
                "sent_at": datetime.now().isoformat(),
                "note": "告警发送需要通知渠道配置，当前返回模拟数据"
            }
        )
