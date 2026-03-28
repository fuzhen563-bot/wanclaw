"""
多租户系统
支持租户隔离、配额管理、套餐管理
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class TenantStatus(Enum):
    """租户状态"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    PENDING = "pending"


class PlanType(Enum):
    """套餐类型"""
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


@dataclass
class Plan:
    """套餐"""
    plan_id: str
    name: str
    plan_type: PlanType
    price: float = 0.0
    max_users: int = 5
    max_stores: int = 1
    max_api_calls: int = 1000
    max_storage_mb: int = 1024
    features: List[str] = field(default_factory=list)
    support_rpa: bool = False
    support_workflow: bool = False
    support_analytics: bool = False


@dataclass
class Quota:
    """配额"""
    max_users: int
    max_stores: int
    max_api_calls: int
    max_storage_mb: int
    api_calls_used: int = 0
    storage_used_mb: int = 0


@dataclass
class Tenant:
    """租户"""
    tenant_id: str
    name: str
    code: str  # 租户代码，用于URL等
    status: TenantStatus = TenantStatus.PENDING
    plan: PlanType = PlanType.FREE
    quota: Quota = None
    config: Dict[str, Any] = field(default_factory=dict)
    admins: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    expired_at: Optional[datetime] = None
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class Store:
    """店铺（租户下的店铺）"""
    store_id: str
    tenant_id: str
    name: str
    platform: str  # 电商平台: taobao, jd, pinduoduo等
    config: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Agent:
    """客服"""
    agent_id: str
    tenant_id: str
    store_id: Optional[str]
    user_id: str
    name: str
    role: str = "operator"  # operator, supervisor, admin
    max_concurrent_chats: int = 5
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)


class PlanManager:
    """套餐管理器"""
    
    def __init__(self):
        self._plans: Dict[str, Plan] = {}
        self._init_default_plans()
    
    def _init_default_plans(self):
        """初始化默认套餐"""
        plans = [
            Plan(
                plan_id="free",
                name="免费版",
                plan_type=PlanType.FREE,
                price=0,
                max_users=3,
                max_stores=1,
                max_api_calls=500,
                max_storage_mb=512,
                features=["基础IM", "基本AI回复"],
            ),
            Plan(
                plan_id="basic",
                name="基础版",
                plan_type=PlanType.BASIC,
                price=99,
                max_users=10,
                max_stores=3,
                max_api_calls=10000,
                max_storage_mb=5120,
                features=["基础IM", "AI回复", "工作流"],
                support_workflow=True,
            ),
            Plan(
                plan_id="professional",
                name="专业版",
                plan_type=PlanType.PROFESSIONAL,
                price=299,
                max_users=50,
                max_stores=10,
                max_api_calls=100000,
                max_storage_mb=51200,
                features=["全功能IM", "AI回复", "工作流", "RPA", "数据分析"],
                support_rpa=True,
                support_workflow=True,
                support_analytics=True,
            ),
            Plan(
                plan_id="enterprise",
                name="企业版",
                plan_type=PlanType.ENTERPRISE,
                price=999,
                max_users=-1,  # 无限制
                max_stores=-1,
                max_api_calls=-1,
                max_storage_mb=-1,
                features=["全功能", "专属客服", "定制开发"],
                support_rpa=True,
                support_workflow=True,
                support_analytics=True,
            ),
        ]
        
        for plan in plans:
            self._plans[plan.plan_id] = plan
    
    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """获取套餐"""
        return self._plans.get(plan_id)
    
    def list_plans(self) -> List[Plan]:
        """列出所有套餐"""
        return list(self._plans.values())


class TenantManager:
    """租户管理器"""
    
    def __init__(self, storage):
        self.storage = storage
        self.plan_manager = PlanManager()
        self._tenants: Dict[str, Tenant] = {}
        self._code_index: Dict[str, str] = {}
    
    async def create_tenant(
        self,
        name: str,
        code: str,
        plan: PlanType = PlanType.FREE,
        admin_user_id: str = None,
        expired_days: int = 30,
    ) -> Tenant:
        """创建租户"""
        tenant_id = f"tenant-{uuid.uuid4().hex[:8]}"
        
        # 获取套餐
        plan_obj = self.plan_manager.get_plan(plan.value)
        quota = Quota(
            max_users=plan_obj.max_users if plan_obj else 3,
            max_stores=plan_obj.max_stores if plan_obj else 1,
            max_api_calls=plan_obj.max_api_calls if plan_obj else 500,
            max_storage_mb=plan_obj.max_storage_mb if plan_obj else 512,
        )
        
        expired_at = datetime.now() + timedelta(days=expired_days) if expired_days > 0 else None
        
        tenant = Tenant(
            tenant_id=tenant_id,
            name=name,
            code=code,
            status=TenantStatus.ACTIVE,
            plan=plan,
            quota=quota,
            admins=[admin_user_id] if admin_user_id else [],
            expired_at=expired_at,
        )
        
        self._tenants[tenant_id] = tenant
        self._code_index[code] = tenant_id
        
        logger.info(f"Tenant created: {tenant_id} ({name})")
        
        return tenant
    
    async def update_tenant(self, tenant_id: str, **updates) -> Optional[Tenant]:
        """更新租户"""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return None
        
        if "name" in updates:
            tenant.name = updates["name"]
        if "plan" in updates:
            tenant.plan = updates["plan"]
            # 更新配额
            plan_obj = self.plan_manager.get_plan(updates["plan"].value)
            if plan_obj:
                tenant.quota = Quota(
                    max_users=plan_obj.max_users,
                    max_stores=plan_obj.max_stores,
                    max_api_calls=plan_obj.max_api_calls,
                    max_storage_mb=plan_obj.max_storage_mb,
                )
        if "status" in updates:
            tenant.status = updates["status"]
        if "config" in updates:
            tenant.config.update(updates["config"])
        
        tenant.updated_at = datetime.now()
        
        return tenant
    
    async def suspend_tenant(self, tenant_id: str) -> bool:
        """暂停租户"""
        return await self.update_tenant(tenant_id, status=TenantStatus.SUSPENDED)
    
    async def activate_tenant(self, tenant_id: str) -> bool:
        """激活租户"""
        return await self.update_tenant(tenant_id, status=TenantStatus.ACTIVE)
    
    async def delete_tenant(self, tenant_id: str) -> bool:
        """删除租户"""
        tenant = self._tenants.get(tenant_id)
        if tenant:
            del self._tenants[tenant_id]
            del self._code_index[tenant.code]
            return True
        return False
    
    async def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """获取租户"""
        return self._tenants.get(tenant_id)
    
    async def get_tenant_by_code(self, code: str) -> Optional[Tenant]:
        """通过代码获取租户"""
        tenant_id = self._code_index.get(code)
        if tenant_id:
            return self._tenants.get(tenant_id)
        return None
    
    async def list_tenants(self, status: TenantStatus = None) -> List[Tenant]:
        """列出租户"""
        tenants = list(self._tenants.values())
        if status:
            tenants = [t for t in tenants if t.status == status]
        return tenants
    
    async def check_quota(self, tenant_id: str) -> Dict[str, Any]:
        """检查配额"""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return {"available": False, "reason": "Tenant not found"}
        
        quota = tenant.quota
        
        # 检查各项配额
        if quota.max_users > 0:
            # 需要查询当前用户数
            pass
        
        return {
            "available": True,
            "quota": {
                "users": {"max": quota.max_users, "used": 0},
                "stores": {"max": quota.max_stores, "used": 0},
                "api_calls": {"max": quota.max_api_calls, "used": quota.api_calls_used},
                "storage": {"max": quota.max_storage_mb, "used": quota.storage_used_mb},
            },
        }
    
    async def consume_api_call(self, tenant_id: str, count: int = 1) -> bool:
        """消耗API调用配额"""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False
        
        quota = tenant.quota
        
        # 检查配额
        if quota.max_api_calls > 0:
            if quota.api_calls_used >= quota.max_api_calls:
                return False
        
        # 消耗配额
        quota.api_calls_used += count
        return True
    
    async def check_expired(self):
        """检查过期租户"""
        now = datetime.now()
        
        for tenant in self._tenants.values():
            if tenant.expired_at and tenant.expired_at < now:
                if tenant.status == TenantStatus.ACTIVE:
                    tenant.status = TenantStatus.EXPIRED
                    logger.warning(f"Tenant expired: {tenant.tenant_id}")


class StoreManager:
    """店铺管理器"""
    
    def __init__(self, tenant_manager: TenantManager):
        self.tenant_manager = tenant_manager
        self._stores: Dict[str, Store] = {}
    
    async def create_store(
        self,
        tenant_id: str,
        name: str,
        platform: str,
        config: Dict = None,
    ) -> Optional[Store]:
        """创建店铺"""
        # 检查租户配额
        quota_check = await self.tenant_manager.check_quota(tenant_id)
        if not quota_check["available"]:
            return None
        
        quota = quota_check["quota"]["stores"]
        # 需要查询当前店铺数
        
        store_id = f"store-{uuid.uuid4().hex[:8]}"
        
        store = Store(
            store_id=store_id,
            tenant_id=tenant_id,
            name=name,
            platform=platform,
            config=config or {},
        )
        
        self._stores[store_id] = store
        
        logger.info(f"Store created: {store_id} for tenant {tenant_id}")
        
        return store
    
    async def update_store(self, store_id: str, **updates) -> Optional[Store]:
        """更新店铺"""
        store = self._stores.get(store_id)
        if not store:
            return None
        
        if "name" in updates:
            store.name = updates["name"]
        if "config" in updates:
            store.config.update(updates["config"])
        if "is_active" in updates:
            store.is_active = updates["is_active"]
        
        return store
    
    async def delete_store(self, store_id: str) -> bool:
        """删除店铺"""
        if store_id in self._stores:
            del self._stores[store_id]
            return True
        return False
    
    async def get_store(self, store_id: str) -> Optional[Store]:
        """获取店铺"""
        return self._stores.get(store_id)
    
    async def list_stores(self, tenant_id: str = None) -> List[Store]:
        """列出店铺"""
        stores = list(self._stores.values())
        if tenant_id:
            stores = [s for s in stores if s.tenant_id == tenant_id]
        return stores


class AgentManager:
    """客服管理器"""
    
    def __init__(self, tenant_manager: TenantManager):
        self.tenant_manager = tenant_manager
        self._agents: Dict[str, Agent] = {}
    
    async def create_agent(
        self,
        tenant_id: str,
        user_id: str,
        name: str,
        store_id: str = None,
        role: str = "operator",
    ) -> Optional[Agent]:
        """创建客服"""
        # 检查租户用户配额
        quota_check = await self.tenant_manager.check_quota(tenant_id)
        if not quota_check["available"]:
            return None
        
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"
        
        agent = Agent(
            agent_id=agent_id,
            tenant_id=tenant_id,
            store_id=store_id,
            user_id=user_id,
            name=name,
            role=role,
        )
        
        self._agents[agent_id] = agent
        
        return agent
    
    async def update_agent(self, agent_id: str, **updates) -> Optional[Agent]:
        """更新客服"""
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        
        if "name" in updates:
            agent.name = updates["name"]
        if "role" in updates:
            agent.role = updates["role"]
        if "max_concurrent_chats" in updates:
            agent.max_concurrent_chats = updates["max_concurrent_chats"]
        if "is_active" in updates:
            agent.is_active = updates["is_active"]
        
        return agent
    
    async def delete_agent(self, agent_id: str) -> bool:
        """删除客服"""
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False
    
    async def get_agent(self, agent_id: str) -> Optional[Agent]:
        """获取客服"""
        return self._agents.get(agent_id)
    
    async def get_agent_by_user(self, user_id: str, tenant_id: str = None) -> Optional[Agent]:
        """通过用户ID获取客服"""
        for agent in self._agents.values():
            if agent.user_id == user_id:
                if tenant_id is None or agent.tenant_id == tenant_id:
                    return agent
        return None
    
    async def list_agents(self, tenant_id: str = None, store_id: str = None) -> List[Agent]:
        """列出客服"""
        agents = list(self._agents.values())
        
        if tenant_id:
            agents = [a for a in agents if a.tenant_id == tenant_id]
        if store_id:
            agents = [a for a in agents if a.store_id == store_id]
        
        return agents


class TenantService:
    """租户服务"""
    
    def __init__(self):
        self.tenant_manager = None
        self.store_manager = None
        self.agent_manager = None
        self.plan_manager = None
    
    async def initialize(self, storage=None):
        """初始化"""
        self.plan_manager = PlanManager()
        self.tenant_manager = TenantManager(storage)
        self.store_manager = StoreManager(self.tenant_manager)
        self.agent_manager = AgentManager(self.tenant_manager)
        
        logger.info("TenantService initialized")
    
    async def create_tenant_with_admin(
        self,
        tenant_name: str,
        tenant_code: str,
        admin_username: str,
        admin_email: str,
        admin_password: str,
        plan: PlanType = PlanType.FREE,
    ) -> Dict[str, Any]:
        """创建租户及管理员"""
        # 1. 创建用户
        from .rbac import UserManager
        user_manager = UserManager(None)
        
        admin_user = await user_manager.create_user(
            username=admin_username,
            email=admin_email,
            password=admin_password,
            full_name="管理员",
            roles=["admin"],
        )
        
        # 2. 创建租户
        tenant = await self.tenant_manager.create_tenant(
            name=tenant_name,
            code=tenant_code,
            plan=plan,
            admin_user_id=admin_user.user_id,
        )
        
        return {
            "tenant": tenant,
            "admin_user": admin_user,
        }


# 全局实例
_tenant_service: Optional[TenantService] = None


async def get_tenant_service() -> TenantService:
    """获取租户服务单例"""
    global _tenant_service
    if _tenant_service is None:
        _tenant_service = TenantService()
        await _tenant_service.initialize()
    return _tenant_service