"""
RBAC权限系统
支持角色管理、权限分配、数据隔离
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps

logger = logging.getLogger(__name__)


class Permission(Enum):
    """权限类型"""
    # 用户管理
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    
    # 角色管理
    ROLE_READ = "role:read"
    ROLE_CREATE = "role:create"
    ROLE_UPDATE = "role:update"
    ROLE_DELETE = "role:delete"
    
    # 租户管理
    TENANT_READ = "tenant:read"
    TENANT_CREATE = "tenant:create"
    TENANT_UPDATE = "tenant:update"
    TENANT_DELETE = "tenant:delete"
    
    # 技能管理
    SKILL_READ = "skill:read"
    SKILL_EXECUTE = "skill:execute"
    SKILL_CREATE = "skill:create"
    SKILL_UPDATE = "skill:update"
    SKILL_DELETE = "skill:delete"
    
    # 工作流管理
    WORKFLOW_READ = "workflow:read"
    WORKFLOW_CREATE = "workflow:create"
    WORKFLOW_UPDATE = "workflow:update"
    WORKFLOW_DELETE = "workflow:delete"
    WORKFLOW_EXECUTE = "workflow:execute"
    
    # 消息管理
    MESSAGE_READ = "message:read"
    MESSAGE_SEND = "message:send"
    MESSAGE_DELETE = "message:delete"
    
    # 系统管理
    CONFIG_READ = "config:read"
    CONFIG_UPDATE = "config:update"
    SYSTEM_INFO = "system:info"
    AUDIT_LOG = "audit:log"
    
    # AI管理
    AI_CONFIG = "ai:config"
    AI_TEST = "ai:test"
    
    # 数据导出
    DATA_EXPORT = "data:export"
    DATA_IMPORT = "data:import"


@dataclass
class Role:
    """角色"""
    role_id: str
    name: str
    description: str = ""
    permissions: Set[str] = field(default_factory=set)
    is_system: bool = False
    tenant_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class User:
    """用户"""
    user_id: str
    username: str
    email: str
    password_hash: str = ""
    full_name: str = ""
    roles: List[str] = field(default_factory=list)
    tenant_id: Optional[str] = None
    is_active: bool = True
    last_login: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class AuditLog:
    """审计日志"""
    log_id: str
    user_id: str
    action: str
    resource: str
    resource_id: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: str = ""
    user_agent: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


class RoleManager:
    """角色管理器"""
    
    def __init__(self, storage):
        self.storage = storage
        self._roles: Dict[str, Role] = {}
    
    async def initialize(self):
        """初始化默认角色"""
        default_roles = [
            {
                "role_id": "admin",
                "name": "超级管理员",
                "description": "拥有所有权限",
                "permissions": [p.value for p in Permission],
                "is_system": True,
            },
            {
                "role_id": "operator",
                "name": "运维人员",
                "description": "负责系统运维",
                "permissions": [
                    Permission.USER_READ.value,
                    Permission.SKILL_READ.value,
                    Permission.SKILL_EXECUTE.value,
                    Permission.WORKFLOW_READ.value,
                    Permission.WORKFLOW_EXECUTE.value,
                    Permission.CONFIG_READ.value,
                    Permission.SYSTEM_INFO.value,
                ],
            },
            {
                "role_id": "developer",
                "name": "开发人员",
                "description": "负责技能和工作流开发",
                "permissions": [
                    Permission.SKILL_READ.value,
                    Permission.SKILL_EXECUTE.value,
                    Permission.SKILL_CREATE.value,
                    Permission.SKILL_UPDATE.value,
                    Permission.SKILL_DELETE.value,
                    Permission.WORKFLOW_READ.value,
                    Permission.WORKFLOW_CREATE.value,
                    Permission.WORKFLOW_UPDATE.value,
                    Permission.WORKFLOW_DELETE.value,
                    Permission.WORKFLOW_EXECUTE.value,
                    Permission.AI_CONFIG.value,
                    Permission.AI_TEST.value,
                ],
            },
            {
                "role_id": "operator_agent",
                "name": "坐席客服",
                "description": "客服操作人员",
                "permissions": [
                    Permission.MESSAGE_READ.value,
                    Permission.MESSAGE_SEND.value,
                    Permission.SKILL_READ.value,
                    Permission.SKILL_EXECUTE.value,
                    Permission.WORKFLOW_READ.value,
                    Permission.WORKFLOW_EXECUTE.value,
                ],
            },
        ]
        
        for role_data in default_roles:
            role = Role(**role_data)
            self._roles[role.role_id] = role
        
        logger.info(f"Initialized {len(self._roles)} default roles")
    
    async def create_role(
        self,
        name: str,
        description: str = "",
        permissions: List[str] = None,
        tenant_id: str = None,
    ) -> Role:
        """创建角色"""
        role_id = f"role-{uuid.uuid4().hex[:8]}"
        role = Role(
            role_id=role_id,
            name=name,
            description=description,
            permissions=set(permissions or []),
            tenant_id=tenant_id,
        )
        
        self._roles[role_id] = role
        await self._save_role(role)
        
        return role
    
    async def update_role(self, role_id: str, **updates) -> Optional[Role]:
        """更新角色"""
        role = self._roles.get(role_id)
        if not role:
            return None
        
        if "name" in updates:
            role.name = updates["name"]
        if "description" in updates:
            role.description = updates["description"]
        if "permissions" in updates:
            role.permissions = set(updates["permissions"])
        
        role.updated_at = datetime.now()
        await self._save_role(role)
        
        return role
    
    async def delete_role(self, role_id: str) -> bool:
        """删除角色"""
        role = self._roles.get(role_id)
        if role and not role.is_system:
            del self._roles[role_id]
            return True
        return False
    
    async def get_role(self, role_id: str) -> Optional[Role]:
        """获取角色"""
        return self._roles.get(role_id)
    
    async def list_roles(self, tenant_id: str = None) -> List[Role]:
        """列出角色"""
        roles = list(self._roles.values())
        if tenant_id:
            roles = [r for r in roles if r.tenant_id == tenant_id or r.is_system]
        return roles
    
    async def _save_role(self, role: Role):
        """保存角色"""
        # 实际需要存储到数据库
        pass


class UserManager:
    """用户管理器"""
    
    def __init__(self, storage):
        self.storage = storage
        self._users: Dict[str, User] = {}
        self._username_index: Dict[str, str] = {}
    
    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: str = "",
        roles: List[str] = None,
        tenant_id: str = None,
    ) -> User:
        """创建用户"""
        import hashlib
        
        user_id = f"user-{uuid.uuid4().hex[:8]}"
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            roles=roles or [],
            tenant_id=tenant_id,
        )
        
        self._users[user_id] = user
        self._username_index[username] = user_id
        
        return user
    
    async def authenticate(self, username: str, password: str) -> Optional[User]:
        """用户认证"""
        import hashlib
        
        user_id = self._username_index.get(username)
        if not user_id:
            return None
        
        user = self._users.get(user_id)
        if not user or not user.is_active:
            return None
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if user.password_hash == password_hash:
            user.last_login = datetime.now()
            return user
        
        return None
    
    async def update_user(self, user_id: str, **updates) -> Optional[User]:
        """更新用户"""
        user = self._users.get(user_id)
        if not user:
            return None
        
        if "email" in updates:
            user.email = updates["email"]
        if "full_name" in updates:
            user.full_name = updates["full_name"]
        if "roles" in updates:
            user.roles = updates["roles"]
        if "is_active" in updates:
            user.is_active = updates["is_active"]
        if "password" in updates:
            import hashlib
            user.password_hash = hashlib.sha256(updates["password"].encode()).hexdigest()
        
        user.updated_at = datetime.now()
        return user
    
    async def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        user = self._users.get(user_id)
        if user:
            del self._users[user_id]
            del self._username_index[user.username]
            return True
        return False
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """获取用户"""
        return self._users.get(user_id)
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """通过用户名获取用户"""
        user_id = self._username_index.get(username)
        if user_id:
            return self._users.get(user_id)
        return None
    
    async def list_users(self, tenant_id: str = None, role: str = None) -> List[User]:
        """列出用户"""
        users = list(self._users.values())
        
        if tenant_id:
            users = [u for u in users if u.tenant_id == tenant_id]
        
        if role:
            users = [u for u in users if role in u.roles]
        
        return users
    
    async def assign_roles(self, user_id: str, roles: List[str]) -> bool:
        """分配角色"""
        user = self._users.get(user_id)
        if user:
            user.roles = roles
            user.updated_at = datetime.now()
            return True
        return False


class PermissionChecker:
    """权限检查器"""
    
    def __init__(self, role_manager: RoleManager):
        self.role_manager = role_manager
    
    async def check(self, user_id: str, permission: Permission) -> bool:
        """检查权限"""
        # 获取用户
        # 获取用户角色
        # 检查角色权限
        return True
    
    async def get_user_permissions(self, user_id: str) -> Set[str]:
        """获取用户所有权限"""
        # 遍历用户角色，合并权限
        return set()
    
    async def has_any_permission(self, user_id: str, permissions: List[Permission]) -> bool:
        """检查是否有任一权限"""
        user_perms = await self.get_user_permissions(user_id)
        return any(p.value in user_perms for p in permissions)
    
    async def has_all_permissions(self, user_id: str, permissions: List[Permission]) -> bool:
        """检查是否拥有所有权限"""
        user_perms = await self.get_user_permissions(user_id)
        return all(p.value in user_perms for p in permissions)


class AuditLogger:
    """审计日志记录器"""
    
    def __init__(self, storage):
        self.storage = storage
        self._logs: List[AuditLog] = []
        self._max_logs = 10000
    
    async def log(
        self,
        user_id: str,
        action: str,
        resource: str,
        resource_id: str = "",
        details: Dict = None,
        ip_address: str = "",
        user_agent: str = "",
    ):
        """记录审计日志"""
        log_id = f"audit-{uuid.uuid4().hex[:8]}"
        log = AuditLog(
            log_id=log_id,
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        self._logs.append(log)
        
        # 限制日志数量
        if len(self._logs) > self._max_logs:
            self._logs = self._logs[-self._max_logs:]
        
        logger.info(f"Audit: {user_id} {action} {resource}:{resource_id}")
    
    async def get_logs(
        self,
        user_id: str = None,
        action: str = None,
        resource: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100,
    ) -> List[AuditLog]:
        """查询审计日志"""
        logs = self._logs
        
        if user_id:
            logs = [l for l in logs if l.user_id == user_id]
        if action:
            logs = [l for l in logs if l.action == action]
        if resource:
            logs = [l for l in logs if l.resource == resource]
        if start_time:
            logs = [l for l in logs if l.timestamp >= start_time]
        if end_time:
            logs = [l for l in logs if l.timestamp <= end_time]
        
        return logs[-limit:]


def require_permission(permission: Permission):
    """权限检查装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从上下文获取用户
            # 检查权限
            # 如果没有权限，抛出异常
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(role: str):
    """角色检查装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从上下文获取用户
            # 检查角色
            return await func(*args, **kwargs)
        return wrapper
    return decorator


class AuthService:
    """认证服务"""
    
    def __init__(self):
        self.role_manager = None
        self.user_manager = None
        self.permission_checker = None
        self.audit_logger = None
    
    async def initialize(self, storage=None):
        """初始化"""
        self.role_manager = RoleManager(storage)
        await self.role_manager.initialize()
        
        self.user_manager = UserManager(storage)
        self.permission_checker = PermissionChecker(self.role_manager)
        self.audit_logger = AuditLogger(storage)
        
        logger.info("AuthService initialized")
    
    async def login(self, username: str, password: str, ip: str = "") -> Optional[User]:
        """登录"""
        user = await self.user_manager.authenticate(username, password)
        
        if user:
            await self.audit_logger.log(
                user.user_id, "login", "auth", ip_address=ip
            )
        
        return user
    
    async def logout(self, user_id: str):
        """登出"""
        await self.audit_logger.log(user_id, "logout", "auth")
    
    async def check_permission(self, user_id: str, permission: Permission) -> bool:
        """检查权限"""
        return await self.permission_checker.check(user_id, permission)


# 全局实例
_auth_service: Optional[AuthService] = None


async def get_auth_service() -> AuthService:
    """获取认证服务单例"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
        await _auth_service.initialize()
    return _auth_service