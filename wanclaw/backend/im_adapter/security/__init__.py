"""
轻量级安全模块
为WanClaw提供基础安全防护
"""

import logging
import re
import os
import hashlib
import hmac
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class SecurityLevel(str, Enum):
    """安全级别"""
    LOW = "low"        # 低风险操作
    MEDIUM = "medium"  # 中风险操作
    HIGH = "high"      # 高风险操作


class OperationType(str, Enum):
    """操作类型"""
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    COMMAND_EXEC = "command_exec"
    PROCESS_MANAGE = "process_manage"
    NETWORK_ACCESS = "network_access"
    SYSTEM_INFO = "system_info"


class SecurityRule(BaseModel):
    """安全规则"""
    id: str = Field(..., description="规则ID")
    name: str = Field(..., description="规则名称")
    description: str = Field(..., description="规则描述")
    pattern: str = Field(..., description="匹配模式（正则表达式）")
    action: str = Field(..., description="执行动作：allow, block, warn")
    severity: SecurityLevel = Field(SecurityLevel.MEDIUM, description="风险级别")
    enabled: bool = Field(True, description="是否启用")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    
    class Config:
        use_enum_values = True


class AuditLog(BaseModel):
    """审计日志"""
    id: str = Field(..., description="日志ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    user_id: str = Field(..., description="用户ID")
    username: Optional[str] = Field(None, description="用户名")
    operation: OperationType = Field(..., description="操作类型")
    resource: str = Field(..., description="操作资源")
    action: str = Field(..., description="执行动作")
    result: str = Field(..., description="执行结果")
    details: Dict[str, Any] = Field(default_factory=dict, description="详细数据")
    ip_address: Optional[str] = Field(None, description="IP地址")
    user_agent: Optional[str] = Field(None, description="用户代理")
    
    class Config:
        use_enum_values = True


class LightweightSecurity:
    """
    轻量级安全模块
    提供基础安全防护功能
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化安全模块
        
        Args:
            config: 安全配置
        """
        self.config = config
        
        # 高危命令列表
        self.high_risk_commands: Set[str] = set(config.get("high_risk_commands", [
            "rm -rf", "rm -rf /", "rm -rf /*",
            "sudo", "su", "chmod 777", "chown",
            "dd if=", "mkfs", "fdisk",
            "shutdown", "reboot", "halt",
            "wget", "curl", "nc", "netcat", "telnet",
            "python -c", "python3 -c",
            "bash -c", "sh -c",
            "> /dev/sda", "dd of=/dev/sda"
        ]))
        
        # 敏感文件路径模式
        self.sensitive_paths: List[str] = config.get("sensitive_paths", [
            r"^/etc/.*", r"^/var/log/.*", r"^/root/.*",
            r"^/home/[^/]+/\.ssh/.*", r"^/proc/.*",
            r".*\.pem$", r".*\.key$", r".*\.secret$",
            r".*\.env$", r".*password.*", r".*credential.*"
        ])
        
        # 允许访问的目录
        self.allowed_dirs: List[str] = config.get("allowed_dirs", [
            "/tmp", "/var/tmp",
            "/home/[^/]+/wanclaw/data",
            "/home/[^/]+/wanclaw/logs",
            "/home/[^/]+/wanclaw/cache"
        ])
        
        # 操作频率限制
        self.rate_limits: Dict[str, Tuple[int, int]] = {
            "file_read": (10, 60),      # 10次/分钟
            "file_write": (5, 60),      # 5次/分钟
            "command_exec": (20, 60),   # 20次/分钟
        }
        
        # 操作计数器
        self.operation_counters: Dict[str, Dict[str, List[datetime]]] = {}
        
        # 审计日志存储
        self.audit_logs: List[AuditLog] = []
        self.max_audit_logs = config.get("max_audit_logs", 10000)
        
        # 安全规则
        self.rules: List[SecurityRule] = self._load_default_rules()
        
        logger.info("安全模块初始化完成")
    
    def _load_default_rules(self) -> List[SecurityRule]:
        """加载默认安全规则"""
        default_rules = [
            SecurityRule(
                id="rule_001",
                name="高危命令拦截",
                description="拦截高危系统命令",
                pattern=r"(rm\s+-rf|sudo\s+rm|chmod\s+777|dd\s+if=|shutdown|reboot)",
                action="block",
                severity=SecurityLevel.HIGH,
                enabled=True
            ),
            SecurityRule(
                id="rule_002",
                name="敏感文件保护",
                description="保护系统敏感文件",
                pattern=r"^(/etc/|/root/|/var/log/|.*\.(pem|key|secret)$)",
                action="block",
                severity=SecurityLevel.HIGH,
                enabled=True
            ),
            SecurityRule(
                id="rule_003",
                name="目录越权访问",
                description="限制目录访问范围",
                pattern=r"^(?!(" + "|".join(self.allowed_dirs) + ")).*",
                action="warn",
                severity=SecurityLevel.MEDIUM,
                enabled=True
            ),
            SecurityRule(
                id="rule_004",
                name="脚本注入检测",
                description="检测可能的脚本注入",
                pattern=r"(bash\s+-c|sh\s+-c|python\s+-c|perl\s+-e)",
                action="warn",
                severity=SecurityLevel.MEDIUM,
                enabled=True
            )
        ]
        return default_rules
    
    def check_command(self, command: str, user_id: str, username: Optional[str] = None) -> Tuple[bool, str]:
        """
        检查命令安全性
        
        Args:
            command: 要执行的命令
            user_id: 用户ID
            username: 用户名
            
        Returns:
            Tuple[是否允许, 原因]
        """
        # 转换为小写进行检查
        cmd_lower = command.lower()
        
        # 检查高危命令
        for risky_cmd in self.high_risk_commands:
            if risky_cmd in cmd_lower:
                self._log_audit(
                    user_id=user_id,
                    username=username,
                    operation=OperationType.COMMAND_EXEC,
                    resource=command,
                    action="block",
                    result=f"高危命令: {risky_cmd}",
                    details={"command": command, "matched_pattern": risky_cmd}
                )
                return False, f"检测到高危命令: {risky_cmd}"
        
        # 应用安全规则
        for rule in self.rules:
            if not rule.enabled:
                continue
                
            if re.search(rule.pattern, command, re.IGNORECASE):
                if rule.action == "block":
                    self._log_audit(
                        user_id=user_id,
                        username=username,
                        operation=OperationType.COMMAND_EXEC,
                        resource=command,
                        action="block",
                        result=f"违反规则: {rule.name}",
                        details={"command": command, "rule_id": rule.id, "rule_name": rule.name}
                    )
                    return False, f"违反安全规则: {rule.name}"
                elif rule.action == "warn":
                    self._log_audit(
                        user_id=user_id,
                        username=username,
                        operation=OperationType.COMMAND_EXEC,
                        resource=command,
                        action="warn",
                        result=f"警告: {rule.name}",
                        details={"command": command, "rule_id": rule.id, "rule_name": rule.name}
                    )
                    # 警告但仍然允许执行
                    return True, f"安全警告: {rule.name}"
        
        # 检查操作频率
        if not self._check_rate_limit(user_id, "command_exec"):
            self._log_audit(
                user_id=user_id,
                username=username,
                operation=OperationType.COMMAND_EXEC,
                resource=command,
                action="block",
                result="操作频率超限",
                details={"command": command, "limit": self.rate_limits["command_exec"]}
            )
            return False, "操作频率超过限制"
        
        # 记录允许的操作
        self._log_audit(
            user_id=user_id,
            username=username,
            operation=OperationType.COMMAND_EXEC,
            resource=command,
            action="allow",
            result="执行成功",
            details={"command": command}
        )
        
        return True, "命令安全检查通过"
    
    def check_file_access(self, file_path: str, operation: OperationType, 
                         user_id: str, username: Optional[str] = None) -> Tuple[bool, str]:
        """
        检查文件访问权限
        
        Args:
            file_path: 文件路径
            operation: 操作类型
            user_id: 用户ID
            username: 用户名
            
        Returns:
            Tuple[是否允许, 原因]
        """
        # 标准化路径
        normalized_path = os.path.abspath(file_path)
        
        # 检查敏感文件
        for pattern in self.sensitive_paths:
            if re.match(pattern, normalized_path):
                self._log_audit(
                    user_id=user_id,
                    username=username,
                    operation=operation,
                    resource=normalized_path,
                    action="block",
                    result="敏感文件访问被拒绝",
                    details={"file_path": normalized_path, "pattern": pattern}
                )
                return False, "禁止访问敏感文件"
        
        # 检查目录权限
        file_allowed = False
        for pattern in self.allowed_dirs:
            if re.match(pattern, normalized_path):
                file_allowed = True
                break
        
        if not file_allowed:
            # 检查是否在允许目录的子目录中
            dir_allowed = False
            parent_dir = os.path.dirname(normalized_path)
            for pattern in self.allowed_dirs:
                if re.match(pattern, parent_dir):
                    dir_allowed = True
                    break
            
            if not dir_allowed:
                self._log_audit(
                    user_id=user_id,
                    username=username,
                    operation=operation,
                    resource=normalized_path,
                    action="block",
                    result="目录访问越权",
                    details={"file_path": normalized_path, "allowed_dirs": self.allowed_dirs}
                )
                return False, "禁止访问该目录"
        
        # 检查操作频率
        op_type = operation.value
        if op_type in self.rate_limits and not self._check_rate_limit(user_id, op_type):
            self._log_audit(
                user_id=user_id,
                username=username,
                operation=operation,
                resource=normalized_path,
                action="block",
                result="操作频率超限",
                details={"file_path": normalized_path, "limit": self.rate_limits[op_type]}
            )
            return False, "操作频率超过限制"
        
        # 记录允许的操作
        self._log_audit(
            user_id=user_id,
            username=username,
            operation=operation,
            resource=normalized_path,
            action="allow",
            result="访问成功",
            details={"file_path": normalized_path, "operation": operation.value}
        )
        
        return True, "文件访问安全检查通过"
    
    def _check_rate_limit(self, user_id: str, operation_type: str) -> bool:
        """
        检查操作频率限制
        
        Args:
            user_id: 用户ID
            operation_type: 操作类型
            
        Returns:
            是否允许继续操作
        """
        if operation_type not in self.rate_limits:
            return True
        
        limit_count, limit_seconds = self.rate_limits[operation_type]
        
        # 初始化计数器
        if user_id not in self.operation_counters:
            self.operation_counters[user_id] = {}
        
        if operation_type not in self.operation_counters[user_id]:
            self.operation_counters[user_id][operation_type] = []
        
        # 清理过期记录
        now = datetime.now()
        valid_time = now.timestamp() - limit_seconds
        
        counters = self.operation_counters[user_id][operation_type]
        counters = [ts for ts in counters if ts.timestamp() > valid_time]
        self.operation_counters[user_id][operation_type] = counters
        
        # 检查是否超限
        if len(counters) >= limit_count:
            return False
        
        # 添加当前操作记录
        counters.append(now)
        return True
    
    def _log_audit(self, user_id: str, username: Optional[str], operation: OperationType,
                   resource: str, action: str, result: str, details: Dict[str, Any]):
        """记录审计日志"""
        audit_log = AuditLog(
            id=f"audit_{len(self.audit_logs) + 1:06d}",
            user_id=user_id,
            username=username,
            operation=operation,
            resource=resource,
            action=action,
            result=result,
            details=details,
            ip_address=None,
            user_agent=None
        )
        
        self.audit_logs.append(audit_log)
        
        # 限制日志数量
        if len(self.audit_logs) > self.max_audit_logs:
            self.audit_logs = self.audit_logs[-self.max_audit_logs:]
        
        # 输出到日志
        log_message = (f"安全审计: user={user_id}, op={operation.value}, "
                      f"resource={resource}, action={action}, result={result}")
        
        if action == "block":
            logger.warning(log_message)
        elif action == "warn":
            logger.info(log_message)
        else:
            logger.debug(log_message)
    
    def get_audit_logs(self, limit: int = 100, user_id: Optional[str] = None,
                      operation: Optional[OperationType] = None) -> List[AuditLog]:
        """
        获取审计日志
        
        Args:
            limit: 返回数量限制
            user_id: 过滤用户ID
            operation: 过滤操作类型
            
        Returns:
            审计日志列表
        """
        logs = self.audit_logs
        
        if user_id:
            logs = [log for log in logs if log.user_id == user_id]
        
        if operation:
            logs = [log for log in logs if log.operation == operation]
        
        # 按时间倒序排序
        logs.sort(key=lambda x: x.timestamp, reverse=True)
        
        return logs[:limit]
    
    def add_rule(self, rule: SecurityRule) -> bool:
        """
        添加安全规则
        
        Args:
            rule: 安全规则
            
        Returns:
            是否添加成功
        """
        # 检查规则ID是否重复
        if any(r.id == rule.id for r in self.rules):
            logger.error(f"规则ID重复: {rule.id}")
            return False
        
        self.rules.append(rule)
        logger.info(f"添加安全规则: {rule.name} (ID: {rule.id})")
        return True
    
    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新安全规则
        
        Args:
            rule_id: 规则ID
            updates: 更新字段
            
        Returns:
            是否更新成功
        """
        for i, rule in enumerate(self.rules):
            if rule.id == rule_id:
                # 更新字段
                for key, value in updates.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)
                
                # 更新时间戳
                rule.updated_at = datetime.now()
                
                logger.info(f"更新安全规则: {rule.name} (ID: {rule_id})")
                return True
        
        logger.error(f"规则不存在: {rule_id}")
        return False
    
    def delete_rule(self, rule_id: str) -> bool:
        """
        删除安全规则
        
        Args:
            rule_id: 规则ID
            
        Returns:
            是否删除成功
        """
        for i, rule in enumerate(self.rules):
            if rule.id == rule_id:
                deleted_rule = self.rules.pop(i)
                logger.info(f"删除安全规则: {deleted_rule.name} (ID: {rule_id})")
                return True
        
        logger.error(f"规则不存在: {rule_id}")
        return False
    
    def get_security_stats(self) -> Dict[str, Any]:
        """获取安全统计信息"""
        now = datetime.now()
        today = now.date()
        
        # 今日日志统计
        today_logs = [log for log in self.audit_logs if log.timestamp.date() == today]
        
        blocked_count = sum(1 for log in today_logs if log.action == "block")
        warned_count = sum(1 for log in today_logs if log.action == "warn")
        allowed_count = sum(1 for log in today_logs if log.action == "allow")
        
        # 按操作类型统计
        op_stats = {}
        for log in today_logs:
            op_type = log.operation  # 已经是字符串
            if op_type not in op_stats:
                op_stats[op_type] = {"total": 0, "blocked": 0, "warned": 0, "allowed": 0}
            
            op_stats[op_type]["total"] += 1
            if log.action == "block":
                op_stats[op_type]["blocked"] += 1
            elif log.action == "warn":
                op_stats[op_type]["warned"] += 1
            elif log.action == "allow":
                op_stats[op_type]["allowed"] += 1
        
        return {
            "total_logs": len(self.audit_logs),
            "today_stats": {
                "total": len(today_logs),
                "blocked": blocked_count,
                "warned": warned_count,
                "allowed": allowed_count
            },
            "operation_stats": op_stats,
            "rule_count": len(self.rules),
            "enabled_rule_count": sum(1 for r in self.rules if r.enabled)
        }


# 全局安全模块实例
_security: Optional[LightweightSecurity] = None


def get_security() -> LightweightSecurity:
    """获取全局安全模块实例"""
    global _security
    if _security is None:
        # 默认配置
        default_config = {
            "high_risk_commands": [
                "rm -rf", "rm -rf /", "rm -rf /*",
                "sudo", "su", "chmod 777", "chown",
                "dd if=", "mkfs", "fdisk",
                "shutdown", "reboot", "halt",
                "wget", "curl", "nc", "netcat", "telnet",
                "python -c", "python3 -c",
                "bash -c", "sh -c",
                "> /dev/sda", "dd of=/dev/sda"
            ],
            "sensitive_paths": [
                r"^/etc/.*", r"^/var/log/.*", r"^/root/.*",
                r"^/home/[^/]+/\.ssh/.*", r"^/proc/.*",
                r".*\.pem$", r".*\.key$", r".*\.secret$",
                r".*\.env$", r".*password.*", r".*credential.*"
            ],
            "allowed_dirs": [
                "/tmp", "/var/tmp",
                "/home/[^/]+/wanclaw/data",
                "/home/[^/]+/wanclaw/logs",
                "/home/[^/]+/wanclaw/cache"
            ],
            "max_audit_logs": 10000
        }
        _security = LightweightSecurity(default_config)
    return _security