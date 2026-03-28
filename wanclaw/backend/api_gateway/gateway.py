"""
API网关
统一入口：路由、认证、限流、监控
"""

import asyncio
import hashlib
import hmac
import json
import logging
import time
import uuid
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from abc import ABC, abstractmethod

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class RateLimitType(Enum):
    """限流类型"""
    PER_USER = "per_user"
    PER_API_KEY = "per_api_key"
    PER_IP = "per_ip"
    GLOBAL = "global"


@dataclass
class APIKey:
    """API密钥"""
    key_id: str
    key_hash: str
    name: str
    user_id: str
    tenant_id: Optional[str] = None
    permissions: List[str] = field(default_factory=list)
    rate_limit: int = 100  # 每分钟
    daily_limit: int = 10000
    expires_at: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class APIRoute:
    """API路由"""
    path: str
    method: str
    handler: Callable
    auth_required: bool = True
    permissions: List[str] = field(default_factory=list)
    rate_limit: int = 100
    timeout: int = 30


@dataclass
class RequestLog:
    """请求日志"""
    request_id: str
    api_key_id: str
    path: str
    method: str
    status_code: int
    duration_ms: int
    ip_address: str
    user_agent: str = ""
    error: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


class RateLimiter:
    """限流器"""
    
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
    
    async def check(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> bool:
        """检查是否允许请求"""
        redis_key = f"ratelimit:{key}"
        
        # 获取当前计数
        current = await self.redis.get(redis_key)
        
        if current is None:
            # 首次请求
            await self.redis.setex(redis_key, window_seconds, 1)
            return True
        
        if int(current) >= limit:
            return False
        
        # 增加计数
        await self.redis.incr(redis_key)
        return True
    
    async def get_remaining(self, key: str, limit: int, window_seconds: int = 60) -> int:
        """获取剩余请求数"""
        redis_key = f"ratelimit:{key}"
        current = await self.redis.get(redis_key)
        
        if current is None:
            return limit
        
        return max(0, limit - int(current))


class APIKeyManager:
    """API密钥管理器"""
    
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
        self._keys: Dict[str, APIKey] = {}
    
    async def create_key(
        self,
        name: str,
        user_id: str,
        tenant_id: str = None,
        permissions: List[str] = None,
        rate_limit: int = 100,
        daily_limit: int = 10000,
        expires_days: int = 365,
    ) -> tuple[str, APIKey]:
        """创建API密钥"""
        key_id = f"ak_{uuid.uuid4().hex[:16]}"
        raw_key = f"sk_{uuid.uuid4().hex[:32]}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        expires_at = datetime.now() + timedelta(days=expires_days) if expires_days > 0 else None
        
        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            user_id=user_id,
            tenant_id=tenant_id,
            permissions=permissions or [],
            rate_limit=rate_limit,
            daily_limit=daily_limit,
            expires_at=expires_at,
        )
        
        # 存储
        key_key = f"apikey:{key_id}"
        await self.redis.hset(key_key, mapping={
            "key_id": key_id,
            "key_hash": key_hash,
            "name": name,
            "user_id": user_id,
            "tenant_id": tenant_id or "",
            "permissions": json.dumps(permissions or []),
            "rate_limit": str(rate_limit),
            "daily_limit": str(daily_limit),
            "expires_at": expires_at.isoformat() if expires_at else "",
            "is_active": "1",
        })
        
        self._keys[key_id] = api_key
        
        # 返回原始密钥（只出现一次）
        return raw_key, api_key
    
    async def verify_key(self, raw_key: str) -> Optional[APIKey]:
        """验证API密钥"""
        if not raw_key.startswith("sk_"):
            return None
        
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        # 查找密钥
        for key_id, key in self._keys.items():
            if key.key_hash == key_hash:
                if not key.is_active:
                    return None
                if key.expires_at and key.expires_at < datetime.now():
                    return None
                return key
        
        return None
    
    async def revoke_key(self, key_id: str) -> bool:
        """撤销API密钥"""
        if key_id in self._keys:
            self._keys[key_id].is_active = False
            await self.redis.hset(f"apikey:{key_id}", "is_active", "0")
            return True
        return False
    
    async def get_key(self, key_id: str) -> Optional[APIKey]:
        """获取API密钥信息"""
        return self._keys.get(key_id)


class RequestLogger:
    """请求日志"""
    
    def __init__(self, redis_client: aioredis.Redis, max_logs: int = 10000):
        self.redis = redis_client
        self.max_logs = max_logs
    
    async def log(self, request_log: RequestLog):
        """记录请求"""
        log_key = f"request_log:{datetime.now().strftime('%Y%m%d')}"
        
        await self.redis.lpush(log_key, json.dumps({
            "request_id": request_log.request_id,
            "api_key_id": request_log.api_key_id,
            "path": request_log.path,
            "method": request_log.method,
            "status_code": request_log.status_code,
            "duration_ms": request_log.duration_ms,
            "ip_address": request_log.ip_address,
            "timestamp": request_log.timestamp.isoformat(),
        }))
        
        # 修剪日志
        await self.redis.ltrim(log_key, 0, self.max_logs)
    
    async def get_logs(
        self,
        key_id: str = None,
        path: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100,
    ) -> List[Dict]:
        """查询请求日志"""
        logs = []
        pattern = "request_log:*"
        
        async for key in self.redis.scan_iter(match=pattern):
            async for log_json in self.redis.lrange(key, 0, -1):
                log = json.loads(log_json)
                
                # 过滤
                if key_id and log.get("api_key_id") != key_id:
                    continue
                if path and log.get("path") != path:
                    continue
                
                logs.append(log)
                
                if len(logs) >= limit:
                    break
        
        return logs[:limit]


class APIGateway:
    """API网关"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None
        
        self.routes: Dict[str, APIRoute] = {}
        self.middleware: List[Callable] = []
        
        self.rate_limiter: Optional[RateLimiter] = None
        self.key_manager: Optional[APIKeyManager] = None
        self.request_logger: Optional[RequestLogger] = None
        
        self._running = False
    
    async def initialize(self):
        """初始化"""
        self.redis = await aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        
        self.rate_limiter = RateLimiter(self.redis)
        self.key_manager = APIKeyManager(self.redis)
        self.request_logger = RequestLogger(self.redis)
        
        self._running = True
        logger.info("APIGateway initialized")
    
    async def close(self):
        """关闭"""
        self._running = False
        if self.redis:
            await self.redis.close()
    
    def register_route(self, route: APIRoute):
        """注册路由"""
        key = f"{route.method}:{route.path}"
        self.routes[key] = route
        logger.info(f"Route registered: {route.method} {route.path}")
    
    def add_middleware(self, middleware: Callable):
        """添加中间件"""
        self.middleware.append(middleware)
    
    async def authenticate(self, request: Dict) -> Optional[APIKey]:
        """认证请求"""
        # 从header获取API密钥
        auth_header = request.get("headers", {}).get("Authorization", "")
        
        if not auth_header.startswith("Bearer "):
            return None
        
        raw_key = auth_header[7:]
        
        return await self.key_manager.verify_key(raw_key)
    
    async def authorize(self, api_key: APIKey, route: APIRoute) -> bool:
        """授权检查"""
        if not route.auth_required:
            return True
        
        # 检查权限
        if route.permissions:
            for perm in route.permissions:
                if perm not in api_key.permissions:
                    return False
        
        return True
    
    async def handle_request(
        self,
        method: str,
        path: str,
        headers: Dict = None,
        query_params: Dict = None,
        body: Dict = None,
        ip: str = "",
    ) -> Dict[str, Any]:
        """处理请求"""
        start_time = time.time()
        request_id = f"req_{uuid.uuid4().hex[:16]}"
        
        headers = headers or {}
        query_params = query_params or {}
        
        # 查找路由
        route_key = f"{method}:{path}"
        route = self.routes.get(route_key)
        
        if not route:
            return {
                "success": False,
                "error": "Not Found",
                "status_code": 404,
                "request_id": request_id,
            }
        
        # 认证
        api_key = await self.authenticate({"headers": headers})
        if route.auth_required and not api_key:
            return {
                "success": False,
                "error": "Unauthorized",
                "status_code": 401,
                "request_id": request_id,
            }
        
        # 授权
        if api_key and not await self.authorize(api_key, route):
            return {
                "success": False,
                "error": "Forbidden",
                "status_code": 403,
                "request_id": request_id,
            }
        
        # 限流
        rate_key = f"{api_key.key_id}:{route.path}" if api_key else ip
        if not await self.rate_limiter.check(rate_key, route.rate_limit):
            return {
                "success": False,
                "error": "Rate limit exceeded",
                "status_code": 429,
                "request_id": request_id,
            }
        
        # 执行中间件
        for mw in self.middleware:
            try:
                if asyncio.iscoroutinefunction(mw):
                    result = await mw(request_id, method, path, headers, query_params, body)
                else:
                    result = mw(request_id, method, path, headers, query_params, body)
                
                if result and result.get("blocked"):
                    return {
                        "success": False,
                        "error": result.get("error", "Blocked"),
                        "status_code": result.get("status_code", 400),
                        "request_id": request_id,
                    }
            except Exception as e:
                logger.error(f"Middleware error: {e}")
        
        # 执行处理器
        try:
            if asyncio.iscoroutinefunction(route.handler):
                result = await asyncio.wait_for(
                    route.handler(api_key, query_params, body),
                    timeout=route.timeout,
                )
            else:
                result = route.handler(api_key, query_params, body)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 记录日志
            if self.request_logger:
                await self.request_logger.log(RequestLog(
                    request_id=request_id,
                    api_key_id=api_key.key_id if api_key else "",
                    path=path,
                    method=method,
                    status_code=200,
                    duration_ms=duration_ms,
                    ip_address=ip,
                ))
            
            return {
                "success": True,
                "data": result,
                "status_code": 200,
                "request_id": request_id,
                "duration_ms": duration_ms,
            }
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Request timeout",
                "status_code": 504,
                "request_id": request_id,
            }
        except Exception as e:
            logger.error(f"Handler error: {e}")
            return {
                "success": False,
                "error": str(e),
                "status_code": 500,
                "request_id": request_id,
            }
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        total_keys = len(self.key_manager._keys) if self.key_manager else 0
        active_keys = sum(1 for k in self.key_manager._keys.values() if k.is_active) if self.key_manager else 0
        
        return {
            "routes": len(self.routes),
            "middleware": len(self.middleware),
            "total_api_keys": total_keys,
            "active_api_keys": active_keys,
        }


# 全局实例
_gateway: Optional[APIGateway] = None


async def get_api_gateway(redis_url: str = "redis://localhost:6379") -> APIGateway:
    """获取API网关单例"""
    global _gateway
    if _gateway is None:
        _gateway = APIGateway(redis_url)
        await _gateway.initialize()
    return _gateway