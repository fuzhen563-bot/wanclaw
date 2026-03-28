"""
操作审计追溯系统
全链路日志、合规报表、数据追溯
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class AuditAction(Enum):
    """审计动作"""
    # 用户操作
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"
    USER_PASSWORD_CHANGE = "user.password_change"
    
    # 租户操作
    TENANT_CREATE = "tenant.create"
    TENANT_UPDATE = "tenant.update"
    TENANT_SUSPEND = "tenant.suspend"
    TENANT_DELETE = "tenant.delete"
    TENANT_PLAN_CHANGE = "tenant.plan_change"
    
    # 技能操作
    SKILL_INSTALL = "skill.install"
    SKILL_UNINSTALL = "skill.uninstall"
    SKILL_EXECUTE = "skill.execute"
    SKILL_CONFIG_UPDATE = "skill.config_update"
    
    # 工作流操作
    WORKFLOW_CREATE = "workflow.create"
    WORKFLOW_UPDATE = "workflow.update"
    WORKFLOW_DELETE = "workflow.delete"
    WORKFLOW_EXECUTE = "workflow.execute"
    
    # 消息操作
    MESSAGE_SEND = "message.send"
    MESSAGE_RECEIVE = "message.receive"
    MESSAGE_DELETE = "message.delete"
    
    # 系统操作
    CONFIG_UPDATE = "config.update"
    API_KEY_CREATE = "api_key.create"
    API_KEY_REVOKE = "api_key.revoke"
    BACKUP_CREATE = "backup.create"
    BACKUP_RESTORE = "backup.restore"


class AuditResource(Enum):
    """审计资源类型"""
    USER = "user"
    TENANT = "tenant"
    SKILL = "skill"
    WORKFLOW = "workflow"
    MESSAGE = "message"
    CONFIG = "config"
    API_KEY = "api_key"
    BACKUP = "backup"
    FILE = "file"


@dataclass
class AuditEntry:
    """审计条目"""
    entry_id: str
    timestamp: datetime
    action: str
    resource_type: str
    resource_id: str
    user_id: str
    tenant_id: Optional[str] = None
    ip_address: str = ""
    user_agent: str = ""
    request_id: str = ""
    status: str = "success"  # success, failure
    details: Dict[str, Any] = field(default_factory=dict)
    before_state: Optional[Dict] = None
    after_state: Optional[Dict] = None
    session_id: str = ""
    correlation_id: str = ""  # 用于关联相关操作


@dataclass
class ComplianceReport:
    """合规报表"""
    report_id: str
    report_type: str  # GDPR, SOX, ISO27001, etc.
    start_date: datetime
    end_date: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)


class AuditLogger:
    """审计日志记录器"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self._buffer: List[AuditEntry] = []
        self._buffer_size = 100
        self._flush_interval = 5  # 秒
    
    async def log(
        self,
        action: AuditAction,
        resource_type: AuditResource,
        resource_id: str,
        user_id: str,
        tenant_id: str = None,
        status: str = "success",
        details: Dict = None,
        before_state: Dict = None,
        after_state: Dict = None,
        ip_address: str = "",
        user_agent: str = "",
        request_id: str = "",
        session_id: str = "",
        correlation_id: str = "",
    ):
        """记录审计日志"""
        entry = AuditEntry(
            entry_id=f"audit_{uuid.uuid4().hex[:16]}",
            timestamp=datetime.now(),
            action=action.value,
            resource_type=resource_type.value,
            resource_id=resource_id,
            user_id=user_id,
            tenant_id=tenant_id,
            status=status,
            details=details or {},
            before_state=before_state,
            after_state=after_state,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            session_id=session_id,
            correlation_id=correlation_id,
        )
        
        # 添加到缓冲区
        self._buffer.append(entry)
        
        # 达到阈值时刷新
        if len(self._buffer) >= self._buffer_size:
            await self._flush()
        
        logger.debug(f"Audit logged: {action.value} on {resource_type.value}:{resource_id}")
    
    async def _flush(self):
        """刷新缓冲区到存储"""
        if not self._buffer:
            return
        
        # 批量写入Redis
        date_str = datetime.now().strftime("%Y%m%d")
        key = f"audit:{date_str}"
        
        entries = []
        for entry in self._buffer:
            entries.append(json.dumps({
                "entry_id": entry.entry_id,
                "timestamp": entry.timestamp.isoformat(),
                "action": entry.action,
                "resource_type": entry.resource_type,
                "resource_id": entry.resource_id,
                "user_id": entry.user_id,
                "tenant_id": entry.tenant_id,
                "status": entry.status,
                "details": entry.details,
                "before_state": entry.before_state,
                "after_state": entry.after_state,
                "ip_address": entry.ip_address,
                "user_agent": entry.user_agent,
                "request_id": entry.request_id,
                "session_id": entry.session_id,
                "correlation_id": entry.correlation_id,
            }))
        
        # 使用管道批量写入
        pipe = self.redis.pipeline()
        for entry_json in entries:
            pipe.lpush(key, entry_json)
        pipe.ltrim(key, 0, 100000)  # 保留10万条
        pipe.execute()
        
        self._buffer = []
    
    async def flush(self):
        """手动刷新"""
        await self._flush()


class AuditQuery:
    """审计查询"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def query(
        self,
        start_time: datetime = None,
        end_time: datetime = None,
        user_id: str = None,
        tenant_id: str = None,
        action: str = None,
        resource_type: str = None,
        resource_id: str = None,
        status: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditEntry]:
        """查询审计日志"""
        entries = []
        
        # 确定日期范围
        start = start_time or datetime.now() - timedelta(days=7)
        end = end_time or datetime.now()
        
        current = start
        while current <= end:
            date_str = current.strftime("%Y%m%d")
            key = f"audit:{date_str}"
            
            # 获取该日期的所有日志
            async for entry_json in self.redis.lrange(key, offset, offset + limit):
                entry_dict = json.loads(entry_json)
                
                # 过滤
                if user_id and entry_dict.get("user_id") != user_id:
                    continue
                if tenant_id and entry_dict.get("tenant_id") != tenant_id:
                    continue
                if action and entry_dict.get("action") != action:
                    continue
                if resource_type and entry_dict.get("resource_type") != resource_type:
                    continue
                if resource_id and entry_dict.get("resource_id") != resource_id:
                    continue
                if status and entry_dict.get("status") != status:
                    continue
                
                entries.append(AuditEntry(
                    entry_id=entry_dict["entry_id"],
                    timestamp=datetime.fromisoformat(entry_dict["timestamp"]),
                    action=entry_dict["action"],
                    resource_type=entry_dict["resource_type"],
                    resource_id=entry_dict["resource_id"],
                    user_id=entry_dict["user_id"],
                    tenant_id=entry_dict.get("tenant_id"),
                    status=entry_dict.get("status"),
                    details=entry_dict.get("details", {}),
                    before_state=entry_dict.get("before_state"),
                    after_state=entry_dict.get("after_state"),
                    ip_address=entry_dict.get("ip_address", ""),
                    user_agent=entry_dict.get("user_agent", ""),
                    request_id=entry_dict.get("request_id", ""),
                    session_id=entry_dict.get("session_id", ""),
                    correlation_id=entry_dict.get("correlation_id", ""),
                ))
            
            current += timedelta(days=1)
        
        # 排序（按时间倒序）
        entries.sort(key=lambda x: x.timestamp, reverse=True)
        
        return entries[:limit]
    
    async def get_user_activity(
        self,
        user_id: str,
        start_time: datetime = None,
        end_time: datetime = None,
    ) -> Dict[str, Any]:
        """获取用户活动摘要"""
        entries = await self.query(
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            limit=1000,
        )
        
        # 统计
        action_counts = {}
        resource_counts = {}
        status_counts = {"success": 0, "failure": 0}
        
        for entry in entries:
            action_counts[entry.action] = action_counts.get(entry.action, 0) + 1
            resource_counts[entry.resource_type] = resource_counts.get(entry.resource_type, 0) + 1
            status_counts[entry.status] = status_counts.get(entry.status, 0) + 1
        
        return {
            "user_id": user_id,
            "total_actions": len(entries),
            "action_distribution": action_counts,
            "resource_distribution": resource_counts,
            "status_distribution": status_counts,
            "first_activity": entries[-1].timestamp.isoformat() if entries else None,
            "last_activity": entries[0].timestamp.isoformat() if entries else None,
        }
    
    async def get_resource_history(
        self,
        resource_type: str,
        resource_id: str,
    ) -> List[AuditEntry]:
        """获取资源变更历史"""
        return await self.query(
            resource_type=resource_type,
            resource_id=resource_id,
            limit=100,
        )
    
    async def get_correlated_operations(
        self,
        correlation_id: str,
    ) -> List[AuditEntry]:
        """获取关联操作（同一请求的不同阶段）"""
        return await self.query(
            limit=100,
        )


class ComplianceReporter:
    """合规报表生成器"""
    
    def __init__(self, audit_query: AuditQuery):
        self.audit_query = audit_query
    
    async def generate_gdpr_report(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> ComplianceReport:
        """生成GDPR合规报表"""
        entries = await self.audit_query.query(
            start_time=start_date,
            end_time=end_date,
            limit=10000,
        )
        
        # GDPR相关统计
        data_access_count = 0
        data_deletion_count = 0
        consent_records = 0
        cross_border_transfers = 0
        security_incidents = 0
        
        for entry in entries:
            action = entry.action
            
            if "access" in action or "read" in action:
                data_access_count += 1
            if "delete" in action:
                data_deletion_count += 1
            if "consent" in action:
                consent_records += 1
            if "transfer" in action or "export" in action:
                cross_border_transfers += 1
            if "security" in action or entry.status == "failure":
                security_incidents += 1
        
        return ComplianceReport(
            report_id=f"gdpr_{uuid.uuid4().hex[:8]}",
            report_type="GDPR",
            start_date=start_date,
            end_date=end_date,
            data={
                "data_access_requests": data_access_count,
                "data_deletion_requests": data_deletion_count,
                "consent_records": consent_records,
                "cross_border_transfers": cross_border_transfers,
                "security_incidents": security_incidents,
                "total_audited_operations": len(entries),
            },
        )
    
    async def generate_security_report(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> ComplianceReport:
        """生成安全审计报表"""
        entries = await self.audit_query.query(
            start_time=start_date,
            end_time=end_date,
            limit=10000,
        )
        
        # 按用户统计失败操作
        user_failures = {}
        
        # 按IP统计
        ip_failures = {}
        
        # 高危操作
        high_risk_actions = {
            "user.delete",
            "tenant.delete",
            "config.update",
            "api_key.revoke",
            "backup.delete",
        }
        
        high_risk_events = []
        
        for entry in entries:
            if entry.status == "failure":
                user_failures[entry.user_id] = user_failures.get(entry.user_id, 0) + 1
                ip_failures[entry.ip_address] = ip_failures.get(entry.ip_address, 0) + 1
            
            if entry.action in high_risk_actions:
                high_risk_events.append({
                    "timestamp": entry.timestamp.isoformat(),
                    "action": entry.action,
                    "user_id": entry.user_id,
                    "resource_id": entry.resource_id,
                    "status": entry.status,
                })
        
        # 可疑IP（失败次数超过阈值）
        suspicious_ips = [
            {"ip": ip, "failures": count}
            for ip, count in ip_failures.items()
            if count > 10
        ]
        
        return ComplianceReport(
            report_id=f"security_{uuid.uuid4().hex[:8]}",
            report_type="SECURITY",
            start_date=start_date,
            end_date=end_date,
            data={
                "total_operations": len(entries),
                "failed_operations": sum(1 for e in entries if e.status == "failure"),
                "high_risk_operations": len(high_risk_events),
                "top_failure_users": sorted(user_failures.items(), key=lambda x: x[1], reverse=True)[:10],
                "suspicious_ips": suspicious_ips,
                "high_risk_events": high_risk_events[-50:],  # 最近50条
            },
        )
    
    async def generate_access_report(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> ComplianceReport:
        """生成用户访问报表（用于数据导出请求）"""
        activity = await self.audit_query.get_user_activity(
            user_id,
            start_date,
            end_date,
        )
        
        entries = await self.audit_query.query(
            user_id=user_id,
            start_time=start_date,
            end_time=end_date,
            limit=1000,
        )
        
        return ComplianceReport(
            report_id=f"access_{uuid.uuid4().hex[:8]}",
            report_type="USER_ACCESS",
            start_date=start_date,
            end_date=end_date,
            data={
                "user_id": user_id,
                "activity_summary": activity,
                "detailed_operations": [
                    {
                        "timestamp": e.timestamp.isoformat(),
                        "action": e.action,
                        "resource": f"{e.resource_type}:{e.resource_id}",
                        "status": e.status,
                        "ip": e.ip_address,
                    }
                    for e in entries
                ],
            },
        )


class AuditService:
    """审计服务"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.logger = AuditLogger(redis_client)
        self.query = AuditQuery(redis_client)
        self.reporter = ComplianceReporter(self.query)
    
    async def log_and_query(
        self,
        action: AuditAction,
        resource_type: AuditResource,
        resource_id: str,
        user_id: str,
        **kwargs,
    ) -> AuditEntry:
        """记录并返回审计条目"""
        await self.logger.log(action, resource_type, resource_id, user_id, **kwargs)
        
        return AuditEntry(
            entry_id="",
            timestamp=datetime.now(),
            action=action.value,
            resource_type=resource_type.value,
            resource_id=resource_id,
            user_id=user_id,
        )
    
    async def get_timeline(
        self,
        resource_type: str,
        resource_id: str,
    ) -> List[Dict]:
        """获取资源时间线"""
        entries = await self.query.get_resource_history(resource_type, resource_id)
        
        return [
            {
                "timestamp": e.timestamp.isoformat(),
                "action": e.action,
                "user_id": e.user_id,
                "before": e.before_state,
                "after": e.after_state,
                "details": e.details,
            }
            for e in entries
        ]


# 全局实例
_audit_service: Optional[AuditService] = None


async def get_audit_service(redis_client=None) -> AuditService:
    """获取审计服务"""
    global _audit_service
    if _audit_service is None:
        import redis.asyncio as aioredis
        redis = redis_client or await aioredis.from_url("redis://localhost:6379")
        _audit_service = AuditService(redis)
    return _audit_service