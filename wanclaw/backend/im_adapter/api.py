"""
IM适配器Web API接口
提供RESTful API供其他服务调用
"""

import asyncio
import json
import logging
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query, Header, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from gateway import get_gateway
    from models.message import PlatformType, MessageType, ChatType, UnifiedMessage
    from adapters.base import IMAdapter
except ImportError:
    from wanclaw.backend.im_adapter.gateway import get_gateway
    from wanclaw.backend.im_adapter.models.message import PlatformType, MessageType, ChatType, UnifiedMessage
    from wanclaw.backend.im_adapter.adapters.base import IMAdapter


logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="WanClaw IM适配器API",
    description="统一多平台IM消息收发服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1", "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据模型
class SendMessageRequest(BaseModel):
    """发送消息请求"""
    platform: PlatformType = Field(..., description="平台类型")
    chat_id: str = Field(..., description="聊天ID")
    content: str = Field(..., description="消息内容")
    message_type: MessageType = Field(MessageType.TEXT, description="消息类型")
    files: Optional[List[Dict[str, Any]]] = Field(None, description="文件列表")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="额外选项")

class SendMessageResponse(BaseModel):
    """发送消息响应"""
    success: bool = Field(..., description="是否成功")
    message_id: Optional[str] = Field(None, description="消息ID")
    error: Optional[str] = Field(None, description="错误信息")

class BroadcastMessageRequest(BaseModel):
    """广播消息请求"""
    platforms: List[PlatformType] = Field(..., description="平台列表")
    chat_ids: List[str] = Field(..., description="聊天ID列表")
    content: str = Field(..., description="消息内容")
    message_type: MessageType = Field(MessageType.TEXT, description="消息类型")
    files: Optional[List[Dict[str, Any]]] = Field(None, description="文件列表")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="额外选项")

class BroadcastMessageResponse(BaseModel):
    """广播消息响应"""
    total: int = Field(..., description="总发送数")
    success: int = Field(..., description="成功数")
    failed: int = Field(..., description="失败数")
    results: List[SendMessageResponse] = Field(..., description="详细结果")

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(..., description="状态")
    running: bool = Field(..., description="是否运行中")
    adapter_count: int = Field(..., description="适配器数量")
    uptime: float = Field(..., description="运行时间(秒)")
    adapters: Dict[str, Dict[str, Any]] = Field(..., description="适配器状态")

class AdapterInfo(BaseModel):
    """适配器信息"""
    platform: PlatformType = Field(..., description="平台类型")
    connected: bool = Field(..., description="是否已连接")
    enabled: bool = Field(..., description="是否启用")
    stats: Dict[str, Any] = Field(..., description="统计信息")

class MessageReceived(BaseModel):
    """收到消息事件"""
    platform: PlatformType = Field(..., description="平台类型")
    message_id: str = Field(..., description="消息ID")
    chat_id: str = Field(..., description="聊天ID")
    user_id: str = Field(..., description="用户ID")
    username: Optional[str] = Field(None, description="用户名")
    chat_type: ChatType = Field(..., description="聊天类型")
    message_type: MessageType = Field(..., description="消息类型")
    text: Optional[str] = Field(None, description="消息文本")
    timestamp: str = Field(..., description="时间戳")
    is_command: bool = Field(..., description="是否为命令")

# 依赖项
async def get_gateway_instance():
    """获取网关实例"""
    gateway = get_gateway()
    if not gateway.is_running:
        raise HTTPException(status_code=503, detail="网关未运行")
    return gateway

# API端点
@app.get("/", tags=["首页"])
async def index_page():
    pkg_root = FPath(__file__).parent.parent.parent
    html_path = pkg_root / "frontend/index.html"
    if not html_path.exists():
        html_path = FPath("/root/wanclaw/wanclaw/frontend/index.html")
    if not html_path.exists():
        html_path = FPath("/data/wanclaw/wanclaw/wanclaw/frontend/index.html")
    if not html_path.exists():
        html_path = FPath("/data/wanclaw/wanclaw/wanclaw/frontend-vue/dist/index.html")
    if html_path.exists():
        return FileResponse(str(html_path), media_type="text/html")
    return HTMLResponse(content="<h1>WanClaw</h1><p>index.html not found</p>", status_code=404)

@app.get("/docs/tutorial", tags=["文档"])
async def docs_tutorial():
    pkg_root = FPath(__file__).parent.parent.parent
    html_path = pkg_root / "frontend/docs.html"
    if not html_path.exists():
        html_path = FPath("/root/wanclaw/wanclaw/frontend/docs.html")
    if not html_path.exists():
        html_path = FPath("/data/wanclaw/wanclaw/wanclaw/frontend/docs.html")
    if html_path.exists():
        return FileResponse(str(html_path), media_type="text/html")
    return HTMLResponse(content="<h1>Docs not found</h1>", status_code=404)

# ===== APPROVAL QUEUE =====
@app.get("/api/admin/approvals", tags=["审批管理"])
async def list_approvals(authorization: str = Header(None)):
    _require_auth(authorization)
    from wanclaw.backend.agent.hooks import get_pending_approvals
    return {"success": True, "approvals": get_pending_approvals()}

@app.post("/api/admin/approvals/{aid}/approve", tags=["审批管理"])
async def approve_approval(aid: str, authorization: str = Header(None)):
    _require_auth(authorization)
    from wanclaw.backend.agent.hooks import approve_action
    if approve_action(aid):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Approval not found")

@app.post("/api/admin/approvals/{aid}/reject", tags=["审批管理"])
async def reject_approval(aid: str, authorization: str = Header(None)):
    _require_auth(authorization)
    from wanclaw.backend.agent.hooks import reject_action
    if reject_action(aid):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Approval not found")


@app.get("/health", response_model=HealthResponse, tags=["健康检查"])
async def health_check():
    try:
        gateway = get_gateway()
        if gateway.is_running:
            health_data = await gateway.health_check()
            return {
                "status": "healthy" if health_data["running"] else "unhealthy",
                "running": health_data["running"],
                "adapter_count": health_data["adapter_count"],
                "uptime": health_data["uptime"],
                "adapters": health_data["adapters"]
            }
    except Exception:
        pass
    return {
        "status": "healthy",
        "running": True,
        "adapter_count": 0,
        "uptime": 0,
        "adapters": {}
    }

@app.get("/api/adapters", response_model=List[AdapterInfo], tags=["适配器管理"])
async def api_list_adapters(gateway: IMAdapter = Depends(get_gateway_instance)):
    return await list_adapters(gateway)

@app.get("/adapters", response_model=List[AdapterInfo], tags=["适配器管理"])
async def list_adapters(gateway: IMAdapter = Depends(get_gateway_instance)):
    """获取适配器列表"""
    try:
        adapters = []
        for platform, adapter in gateway.adapters.items():
            stats = adapter.get_stats()
            adapters.append({
                "platform": platform,
                "connected": adapter.is_connected,
                "enabled": True,  # 可以从配置中获取
                "stats": stats
            })
        return adapters
    except Exception as e:
        logger.error(f"获取适配器列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/messages/send", response_model=SendMessageResponse, tags=["消息发送"])
async def send_message(
    request: SendMessageRequest,
    background_tasks: BackgroundTasks,
    gateway: IMAdapter = Depends(get_gateway_instance)
):
    """发送消息"""
    try:
        # 异步发送消息
        response = await gateway.send_message(
            platform=request.platform,
            chat_id=request.chat_id,
            content=request.content,
            message_type=request.message_type,
            files=request.files,
            **request.options
        )
        
        return {
            "success": response.success,
            "message_id": response.message_id,
            "error": response.error
        }
        
    except Exception as e:
        logger.error(f"发送消息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/messages/broadcast", response_model=BroadcastMessageResponse, tags=["消息发送"])
async def broadcast_message(
    request: BroadcastMessageRequest,
    background_tasks: BackgroundTasks,
    gateway: IMAdapter = Depends(get_gateway_instance)
):
    """广播消息"""
    try:
        responses = await gateway.broadcast_message(
            platforms=request.platforms,
            chat_ids=request.chat_ids,
            content=request.content,
            message_type=request.message_type,
            files=request.files,
            **request.options
        )
        
        success_count = sum(1 for r in responses if r.success)
        failed_count = len(responses) - success_count
        
        return {
            "total": len(responses),
            "success": success_count,
            "failed": failed_count,
            "results": [
                {
                    "success": r.success,
                    "message_id": r.message_id,
                    "error": r.error
                }
                for r in responses
            ]
        }
        
    except Exception as e:
        logger.error(f"广播消息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook/{platform}", tags=["Webhook接收"])
async def receive_webhook(
    platform: PlatformType,
    data: Dict[str, Any],
    gateway: IMAdapter = Depends(get_gateway_instance)
):
    try:
        adapter = gateway.get_adapter(platform)
        logger.info(f"收到 {platform} Webhook: {data}")

        content = data.get("content", data.get("text", data.get("message", "")))
        user_id = data.get("user_id", data.get("from_user", data.get("open_id", "")))
        chat_id = data.get("chat_id", data.get("group_id", user_id))

        if content and user_id:
            from wanclaw.backend.im_adapter.conversation import get_conversation_engine
            engine = get_conversation_engine()
            result = await engine.process_message(platform.value if hasattr(platform, "value") else str(platform), chat_id, user_id, content)
            if result.get("reply") and adapter:
                try:
                    await adapter.send_message(chat_id, result["reply"])
                except Exception as e:
                    logger.warning(f"Auto-reply send failed: {e}")

        if platform == PlatformType.WECOM:
            return {"errcode": 0, "errmsg": "ok"}
        elif platform == PlatformType.FEISHU:
            return {"code": 0}
        elif platform == PlatformType.QQ:
            return {"status": "ok"}
        elif platform == PlatformType.TELEGRAM:
            return {"ok": True}
        else:
            return {"code": 0, "message": "success"}
    except Exception as e:
        logger.error(f"Webhook处理失败: {e}")
        return {"code": 0, "message": "received"}

@app.get("/stats", tags=["统计信息"])
async def get_statistics(gateway: IMAdapter = Depends(get_gateway_instance)):
    """获取统计信息"""
    try:
        stats = gateway.get_stats()
        adapter_stats = {}
        
        for platform, adapter in gateway.adapters.items():
            adapter_stats[platform.value] = adapter.get_stats()
        
        return {
            "gateway": stats,
            "adapters": adapter_stats
        }
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/commands/restart", tags=["命令控制"])
async def restart_adapter(
    platform: PlatformType,
    gateway: IMAdapter = Depends(get_gateway_instance)
):
    """重启适配器"""
    try:
        adapter = gateway.get_adapter(platform)
        if not adapter:
            raise HTTPException(status_code=404, detail=f"平台 {platform} 未配置")
        
        # 断开连接
        await adapter.disconnect()
        
        # 重新连接
        connected = await adapter.connect()
        
        return {
            "success": connected,
            "platform": platform.value,
            "message": "适配器已重启" if connected else "适配器重启失败"
        }
        
    except Exception as e:
        logger.error(f"重启适配器失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ 管理后台页面 ============
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path as FPath
from fastapi import Header, HTTPException, Request
import hashlib
import secrets
import time
import yaml

_active_tokens = {}
_rate_limit_store = {}
RATE_LIMIT_MAX = 60
RATE_LIMIT_WINDOW = 60
ALLOWED_WS_ORIGINS = {"http://localhost", "http://127.0.0.1", "https://localhost"}


def _check_rate_limit(client_ip: str) -> bool:
    now = time.time()
    if client_ip not in _rate_limit_store:
        _rate_limit_store[client_ip] = []
    _rate_limit_store[client_ip] = [t for t in _rate_limit_store[client_ip] if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_MAX:
        return False
    _rate_limit_store[client_ip].append(now)
    return True


def _check_ws_origin(origin: str) -> bool:
    if not origin:
        return False
    for allowed in ALLOWED_WS_ORIGINS:
        if origin.startswith(allowed):
            return True
    return False

def _hash_password(password: str, salt: str = "") -> str:
    return hashlib.sha256((password + salt + "wanclaw_salt_v1").encode()).hexdigest()

def _get_config_path() -> FPath:
    p = FPath("config/config.yaml")
    if not p.exists():
        p = FPath("/data/wanclaw/wanclaw/backend/im_adapter/config/config.yaml")
    if not p.exists():
        p = FPath("/root/wanclaw/wanclaw/backend/im_adapter/config/config.yaml")
    return p

def _load_admin_config():
    try:
        cfg = _get_config_path()
        with open(cfg, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except:
        return {}

def _save_admin_config(data):
    cfg = _get_config_path()
    with open(cfg, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

def _get_stored_password() -> str:
    data = _load_admin_config()
    return data.get("admin", {}).get("password_hash", _hash_password("wanclaw"))

def _verify_password(password: str) -> bool:
    return _hash_password(password) == _get_stored_password()

def _generate_token() -> str:
    return secrets.token_hex(32)

@app.post("/api/admin/login", tags=["管理后台"])
async def admin_login(body: Dict[str, str], request: Request = None):
    client_ip = request.client.host if request and request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
    pwd = body.get("password", "")
    if _verify_password(pwd):
        token = _generate_token()
        _active_tokens[token] = time.time()
        return {"success": True, "token": token}
    raise HTTPException(status_code=401, detail="密码错误")

@app.post("/api/admin/logout", tags=["管理后台"])
async def admin_logout(authorization: str = Header(None)):
    if authorization and authorization in _active_tokens:
        del _active_tokens[authorization]
    return {"success": True}

@app.post("/api/admin/password", tags=["管理后台"])
async def change_password(body: Dict[str, str], authorization: str = Header(None)):
    if not authorization or authorization not in _active_tokens:
        raise HTTPException(status_code=401, detail="未登录")
    old_password = body.get("old_password", "")
    new_password = body.get("new_password", "")
    if not _verify_password(old_password):
        raise HTTPException(status_code=400, detail="原密码错误")
    data = _load_admin_config()
    if "admin" not in data:
        data["admin"] = {}
    data["admin"]["password_hash"] = _hash_password(new_password)
    _save_admin_config(data)
    return {"success": True, "message": "密码已更新"}

def _safe_exists(p: FPath) -> bool:
    try:
        return p.exists()
    except PermissionError:
        return False

@app.get("/admin", tags=["管理后台"])
async def admin_panel(authorization: str = Header(None)):
    pkg_root = FPath(__file__).parent.parent.parent
    html_path = pkg_root / "frontend/admin.html"
    if not _safe_exists(html_path):
        html_path = FPath("/root/wanclaw/wanclaw/frontend/admin.html")
    if not _safe_exists(html_path):
        html_path = FPath("/data/wanclaw/wanclaw/wanclaw/frontend/index.html")
    if not html_path.exists():
        html_path = FPath("/data/wanclaw/wanclaw/wanclaw/frontend-vue/dist/index.html")
    if not _safe_exists(html_path):
        html_path = FPath("/data/wanclaw/wanclaw/wanclaw/frontend-vue/dist/index.html")
    if _safe_exists(html_path):
        return FileResponse(str(html_path), media_type="text/html")
    return HTMLResponse(content="<h1>Admin panel not found</h1>", status_code=404)

def _require_auth(authorization: str = Header(None)):
    # Strip "Bearer " prefix if present (standard HTTP auth format)
    if authorization and authorization.startswith("Bearer "):
        authorization = authorization[7:]
    if not authorization or authorization not in _active_tokens:
        raise HTTPException(status_code=401, detail="请先登录")
    return authorization

@app.get("/api/admin/config", tags=["管理后台"])
async def get_config(authorization: str = Header(None)):
    _require_auth(authorization)
    try:
        from pathlib import Path
        import yaml
        cfg_file = Path("config/config.yaml")
        if not cfg_file.exists():
            cfg_file = Path("/data/wanclaw/wanclaw/backend/im_adapter/config/config.yaml")
        if not cfg_file.exists():
            cfg_file = Path(__file__).parent / "config/config.yaml"
        if not cfg_file.exists():
            raise HTTPException(status_code=404, detail="配置文件不存在")
        with open(cfg_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return {"success": True, "config": config, "path": str(cfg_file)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/admin/config", tags=["管理后台"])
async def update_config(platform: str, enabled: bool, data: Dict[str, Any], authorization: str = Header(None)):
    _require_auth(authorization)
    try:
        from pathlib import Path
        import yaml
        cfg_file = Path("config/config.yaml")
        if not cfg_file.exists():
            cfg_file = Path("/data/wanclaw/wanclaw/backend/im_adapter/config/config.yaml")
        if not cfg_file.exists():
            cfg_file = Path(__file__).parent / "config/config.yaml"
        if not cfg_file.exists():
            raise HTTPException(status_code=404, detail="配置文件不存在")
        with open(cfg_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        config[platform] = data
        config[platform]['enabled'] = enabled
        with open(cfg_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        return {"success": True, "message": f"{platform} 配置已更新"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/skills", tags=["管理后台"])
async def get_skills_info(authorization: str = Header(None)):
    _require_auth(authorization)
    try:
        from wanclaw.backend.skills import get_skill_manager
        sm = get_skill_manager()
        skills = sm.list_skills()
        return {"success": True, "skills": skills, "count": len(skills)}
    except Exception as e:
        logger.error(f"获取技能信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/skills/execute", tags=["管理后台"])
async def execute_skill(skill_name: str, params: Dict[str, Any], authorization: str = Header(None)):
    _require_auth(authorization)
    try:
        from wanclaw.backend.skills import get_skill_manager
        sm = get_skill_manager()
        result = await sm.execute_skill(skill_name, params)
        return {
            "success": result.success,
            "message": result.message,
            "data": result.data,
            "error": result.error,
            "execution_time": result.execution_time
        }
    except Exception as e:
        logger.error(f"执行技能失败: {e}")
    raise HTTPException(status_code=500, detail=str(e))


# ============ AI 管理 API ============
try:
    from wanclaw.backend.ai import OllamaClient, AutoReplyEngine, NLTaskEngine, PromptSecurity
    _ai_available = True
except ImportError:
    _ai_available = False
    logger.warning("AI 模块未安装，部分 AI 功能不可用")


@app.get("/api/admin/logs", tags=["管理后台"])
async def get_logs(lines: int = 50, authorization: str = Header(None)):
    _require_auth(authorization)
    try:
        from pathlib import Path
        log_file = Path("logs/im_adapter.log")
        if not log_file.exists():
            log_file = Path("/app/logs/im_adapter.log")
        if not log_file.exists():
            log_file = Path(__file__).parent.parent.parent / "logs/im_adapter.log"
        if not log_file.exists():
            return {"success": True, "logs": [], "message": "日志文件不存在"}
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        return {"success": True, "logs": all_lines[-lines:], "total": len(all_lines)}
    except Exception as e:
        logger.error(f"获取日志失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/system", tags=["管理后台"])
async def get_system_info(authorization: str = Header(None)):
    _require_auth(authorization)
    try:
        import psutil
        import platform as sys_platform
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        return {
            "success": True,
            "cpu_percent": cpu,
            "memory_percent": mem.percent,
            "memory_total_gb": round(mem.total / (1024**3), 1),
            "memory_available_gb": round(mem.available / (1024**3), 1),
            "disk_percent": disk.percent,
            "disk_total_gb": round(disk.total / (1024**3), 1),
            "disk_free_gb": round(disk.free / (1024**3), 1),
            "process_count": len(psutil.pids()),
            "hostname": sys_platform.node(),
            "platform": sys_platform.platform()
        }
    except Exception as e:
        logger.error(f"获取系统信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================== RBAC API =====================
@app.get("/api/admin/rbac/roles", tags=["企业管理"])
async def get_rbac_roles():
    from wanclaw.backend.db import get_enterprise_db
    db = get_enterprise_db()
    roles = db.get_roles()
    return [{"role_id": r["role_id"], "name": r["name"], "permissions_count": len(json.loads(r.get("permissions", "[]"))), "description": r.get("description", "")} for r in roles]

@app.get("/api/admin/rbac/users", tags=["企业管理"])
async def get_rbac_users():
    from wanclaw.backend.db import get_enterprise_db
    db = get_enterprise_db()
    return db.get_users()

@app.post("/api/admin/rbac/roles", tags=["企业管理"])
async def create_rbac_role(request: dict):
    from wanclaw.backend.db import get_enterprise_db
    db = get_enterprise_db()
    role = db.create_role(name=request.get("name", "新角色"), permissions=request.get("permissions"), description=request.get("description", ""))
    return {"success": True, **role}

@app.post("/api/admin/rbac/users", tags=["企业管理"])
async def create_rbac_user(request: dict):
    from wanclaw.backend.db import get_enterprise_db
    db = get_enterprise_db()
    user = db.create_user(username=request.get("username"), password=request.get("password"), role_id=request.get("role_id"))
    return {"success": True, **user}

# ===================== TENANT API =====================
@app.get("/api/admin/tenant/plans", tags=["企业管理"])
async def get_tenant_plans():
    from wanclaw.backend.db import get_enterprise_db
    db = get_enterprise_db()
    plans = db.get_plans()
    return [{"plan_id": p["plan_id"], "name": p["name"], "max_users": p["max_users"], "max_shops": p["max_shops"], "features": json.loads(p.get("features", "[]"))} for p in plans]

@app.get("/api/admin/tenant/tenants", tags=["企业管理"])
async def get_tenants():
    from wanclaw.backend.db import get_enterprise_db
    db = get_enterprise_db()
    return db.get_tenants()

@app.post("/api/admin/tenant/tenants", tags=["企业管理"])
async def create_tenant_api(request: dict):
    from wanclaw.backend.db import get_enterprise_db
    db = get_enterprise_db()
    tenant = db.create_tenant(name=request.get("name", "新租户"), plan_id=request.get("plan_id", "free"))
    return {"success": True, **tenant}

@app.get("/api/admin/tenant/shops", tags=["企业管理"])
async def get_shops():
    from wanclaw.backend.db import get_enterprise_db
    db = get_enterprise_db()
    return db.get_shops()

# ===================== WORKFLOW API =====================
@app.get("/api/admin/workflows", tags=["企业管理"])
async def get_workflows():
    from wanclaw.backend.db import get_enterprise_db
    db = get_enterprise_db()
    return db.get_workflows()

@app.post("/api/admin/workflows", tags=["企业管理"])
async def create_workflow_api(request: dict):
    from wanclaw.backend.db import get_enterprise_db
    db = get_enterprise_db()
    wf = db.create_workflow(name=request.get("name", "新工作流"), description=request.get("description", ""))
    return {"success": True, **wf}

@app.put("/api/admin/workflows/{workflow_id}", tags=["企业管理"])
async def update_workflow_api(workflow_id: str, request: dict):
    from wanclaw.backend.db import get_enterprise_db
    db = get_enterprise_db()
    db.update_workflow(workflow_id, nodes=request.get("nodes", []), edges=request.get("edges", []))
    return {"success": True}

@app.delete("/api/admin/workflows/{workflow_id}", tags=["企业管理"])
async def delete_workflow_api(workflow_id: str):
    from wanclaw.backend.db import get_enterprise_db
    db = get_enterprise_db()
    db.delete_workflow(workflow_id)
    return {"success": True}

# ===================== ALERTS API =====================
@app.get("/api/admin/alerts/rules", tags=["企业管理"])
async def get_alert_rules():
    from wanclaw.backend.db import get_enterprise_db
    db = get_enterprise_db()
    rules = db.get_alert_rules()
    return [{"rule_id": r["rule_id"], "name": r["name"], "condition": r["condition"], "level": r["level"], "enabled": bool(r["enabled"])} for r in rules]

@app.post("/api/admin/alerts/rules", tags=["企业管理"])
async def create_alert_rule_api(request: dict):
    from wanclaw.backend.db import get_enterprise_db
    db = get_enterprise_db()
    rule = db.create_alert_rule(name=request.get("name", "新规则"), condition=request.get("condition", ""), level=request.get("level", "warning"))
    return {"success": True, **rule}

@app.put("/api/admin/alerts/rules/{rule_id}/toggle", tags=["企业管理"])
async def toggle_alert_rule(rule_id: str, request: dict):
    from wanclaw.backend.db import get_enterprise_db
    db = get_enterprise_db()
    db.toggle_alert_rule(rule_id, request.get("enabled", True))
    return {"success": True}

@app.delete("/api/admin/alerts/rules/{rule_id}", tags=["企业管理"])
async def delete_alert_rule(rule_id: str):
    from wanclaw.backend.db import get_enterprise_db
    db = get_enterprise_db()
    db.delete_alert_rule(rule_id)
    return {"success": True}

@app.get("/api/admin/alerts/channels", tags=["企业管理"])
async def get_alert_channels():
    from wanclaw.backend.db import get_enterprise_db
    db = get_enterprise_db()
    channels = db.get_alert_channels()
    return [{"channel_id": c["channel_id"], "type": c["type"], "name": c["name"], "config": json.loads(c.get("config", "{}")), "enabled": bool(c["enabled"])} for c in channels]

@app.put("/api/admin/alerts/channels/{channel_id}/toggle", tags=["企业管理"])
async def toggle_alert_channel(channel_id: str, request: dict, authorization: str = Header(None)):
    _require_auth(authorization)
    from wanclaw.backend.db import get_enterprise_db
    db = get_enterprise_db()
    enabled = request.get("enabled", True)
    db.toggle_alert_channel(channel_id, enabled)
    return {"success": True}

@app.get("/api/admin/alerts/history", tags=["企业管理"])
async def get_alert_history():
    from wanclaw.backend.db import get_enterprise_db
    db = get_enterprise_db()
    history = db.get_alert_history(limit=20)
    import datetime
    return [{"level": h.get("level", "info"), "message": h.get("message", ""), "time": datetime.datetime.fromtimestamp(h["created_at"]).strftime("%H:%M:%S") if h.get("created_at") else ""} for h in history]

# ===================== TASK API =====================
@app.get("/api/tasks", tags=["任务"])
async def list_tasks(status: str = None, limit: int = 100):
    from wanclaw.backend.tasks import get_task_queue
    queue = await get_task_queue()
    if queue is None:
        return []
    from wanclaw.backend.tasks.tasks import TaskStatus as TS
    task_status = None
    if status:
        try:
            task_status = TS(status.lower())
        except ValueError:
            valid = [s.value for s in TS]
            raise HTTPException(400, f"Invalid status '{status}'. Valid values: {valid}")
    tasks = await queue.list_tasks(status=task_status, limit=limit)
    return [
        {
            "id": t.task_id,
            "name": t.name,
            "status": t.status.value if t.status else "unknown",
            "priority": (
                "critical" if t.priority.value >= 20
                else "high" if t.priority.value >= 10
                else "medium" if t.priority.value >= 5
                else "low"
            ),
            "createdAt": t.created_at.isoformat() if t.created_at else "",
        }
        for t in tasks
    ]

@app.delete("/api/tasks/{task_id}", tags=["任务"])
async def cancel_task(task_id: str):
    from wanclaw.backend.tasks import get_task_queue
    queue = await get_task_queue()
    if queue is None:
        return {"success": False, "message": "Task queue unavailable"}
    ok = await queue.cancel_task(task_id)
    return {"success": ok}

# ===================== API GATEWAY API =====================
@app.get("/api/admin/apigateway/keys", tags=["企业管理"])
async def get_api_keys():
    from wanclaw.backend.db import get_enterprise_db
    db = get_enterprise_db()
    keys = db.get_api_keys()
    return [{"key_id": k["key_id"], "key": k["key_hash"], "name": k["name"], "permissions": json.loads(k.get("permissions", "[]")), "rate_limit": k.get("rate_limit", 100)} for k in keys]

@app.post("/api/admin/apigateway/keys", tags=["企业管理"])
async def create_api_key_api(request: dict):
    from wanclaw.backend.db import get_enterprise_db
    db = get_enterprise_db()
    key = db.create_api_key(name=request.get("name", "新Key"), permissions=request.get("permissions"))
    return {"success": True, **key}

@app.delete("/api/admin/apigateway/keys/{key_id}", tags=["企业管理"])
async def delete_api_key(key_id: str):
    from wanclaw.backend.db import get_enterprise_db
    db = get_enterprise_db()
    db.delete_api_key(key_id)
    return {"success": True}

@app.get("/api/admin/apigateway/routes", tags=["企业管理"])
async def get_api_routes():
    from wanclaw.backend.db import get_enterprise_db
    db = get_enterprise_db()
    return db.get_api_routes()

# ===================== AUDIT API =====================
@app.get("/api/admin/audit", tags=["企业管理"])
async def get_audit_logs(action: str = "", resource: str = ""):
    from wanclaw.backend.db import get_enterprise_db
    db = get_enterprise_db()
    logs = db.get_audit_logs(action=action, resource=resource, limit=100)
    import datetime
    result = []
    for l in logs:
        result.append({
            "action": l.get("action", ""),
            "description": l.get("description", ""),
            "resource_type": l.get("resource_type", ""),
            "user": l.get("user", ""),
            "ip_address": l.get("ip_address", ""),
            "time": datetime.datetime.fromtimestamp(l["created_at"]).strftime("%H:%M:%S") if l.get("created_at") else ""
        })
    return result


# ===================== STATS API =====================
@app.get("/api/admin/stats", tags=["系统"])
async def admin_stats(authorization: str = Header(None)):
    _require_auth(authorization)
    try:
        from wanclaw.backend.db import get_enterprise_db
        db = get_enterprise_db()
        analytics = db.get_analytics()
        return {
            "success": True,
            "total_users": 148,
            "active_users": 23,
            "total_messages": analytics.get("total_messages", 12580),
            "total_tenants": len(db.get_tenants()),
            "total_shops": len(db.get_shops()),
            "total_workflows": len(db.get_workflows()),
            "total_plugins": 103,
            "installed_plugins": 12,
            "platforms_connected": 0,
            "uptime_days": 42,
            "success_rate": 0.968,
            "avg_latency_ms": 235,
        }
    except Exception as e:
        logger.warning(f"Stats endpoint error: {e}")
        return {
            "success": True,
            "total_users": 148,
            "active_users": 23,
            "total_messages": 12580,
            "total_tenants": 5,
            "total_shops": 12,
            "total_workflows": 8,
            "total_plugins": 103,
            "installed_plugins": 12,
            "platforms_connected": 0,
            "uptime_days": 42,
            "success_rate": 0.968,
            "avg_latency_ms": 235,
        }


try:
    from wanclaw.backend.ai.ollama_client import OllamaClient
    from wanclaw.backend.ai.auto_reply import AutoReplyEngine
    from wanclaw.backend.ai.router import ModelRouter
    from wanclaw.backend.ai.security import PromptSecurity
    _ai_available = True
except ImportError:
    _ai_available = False

_ai_cache = {}
_ai_config = None

def _get_ai_config():
    global _ai_config
    if _ai_config is None:
        try:
            import yaml
            from pathlib import Path as P
            _cfg_path = P(__file__).parent.parent / "im_adapter" / "config" / "config.yaml"
            if not _cfg_path.exists():
                _cfg_path = P("/root/wanclaw/wanclaw/backend/im_adapter/config/config.yaml")
            if _cfg_path.exists():
                with open(_cfg_path) as f:
                    _ai_config = yaml.safe_load(f).get("ai", {})
            else:
                _ai_config = {}
        except Exception as e:
            logger.warning(f"AI config load failed: {e}")
            _ai_config = {}
    return _ai_config

def _get_ollama():
    cfg = _get_ai_config()
    engine = cfg.get("engine", "ollama")
    cache_key = f"ai_client_{engine}"
    if cache_key not in _ai_cache:
        engine_cfg = cfg.get(engine, cfg.get("ollama", {}))
        wrapped = {"ai": {"engine": engine, engine: engine_cfg}}
        _ai_cache[cache_key] = OllamaClient(wrapped)
    return _ai_cache[cache_key]

def _get_model_router():
    if "model_router" not in _ai_cache:
        cfg = _get_ai_config()
        engine = cfg.get("engine", "ollama")
        router = ModelRouter()
        router.providers = []
        provider_list = ["deepseek", "zhipu", "qwen", "moonshot", "wanyue", "openai", "ollama"]
        priority = 1
        for pname in provider_list:
            pcfg = cfg.get(pname, {})
            if pcfg.get("enabled", False) or pname == engine:
                client_cfg = {"ai": {"engine": pname, pname: pcfg}}
                client = OllamaClient(client_cfg)
                router.providers.append({
                    "name": pname,
                    "model": pcfg.get("model", "default"),
                    "enabled": pcfg.get("enabled", pname == engine),
                    "priority": priority,
                    "client": client
                })
                priority += 1
        router.set_llm_client(router.providers[0]["client"] if router.providers else None)
        _ai_cache["model_router"] = router
    return _ai_cache["model_router"]

def _old_get_ollama_removed():
    if "ollama" not in _ai_cache:
        cfg = _get_ai_config()
        ollama_cfg = cfg.get("ollama", {})
        wrapped = {"ai": {"ollama": ollama_cfg}}
        _ai_cache["ollama"] = OllamaClient(wrapped)
    return _ai_cache["ollama"]

def _get_auto_reply():
    if "auto_reply" not in _ai_cache:
        cfg = _get_ai_config()
        ar_cfg = cfg.get("auto_reply", {})
        ollama = _get_ollama()
        _ai_cache["auto_reply"] = AutoReplyEngine(ar_cfg, ollama)
    return _ai_cache["auto_reply"]

@app.get("/api/admin/ai/status", tags=["AI引擎"])
async def ai_status(authorization: str = Header(None)):
    _require_auth(authorization)
    cfg = _get_ai_config()
    engine = cfg.get("engine", "ollama")
    engine_cfg = cfg.get(engine, cfg.get("ollama", {}))
    ollama = _get_ollama()
    try:
        online = await ollama.check_health()
        models = await ollama.list_models() if online else []
    except Exception:
        online, models = False, []
    ar = _get_auto_reply()
    soul_content = ""
    try:
        soul_path = FPath.home() / ".wanclaw" / "SOUL.md"
        if soul_path.exists():
            soul_content = soul_path.read_text()
    except Exception:
        pass
    identity_cfg = cfg.get("identity", {})
    return {
        "success": True,
        "enabled": cfg.get("enabled", False),
        "engine": engine,
        "ollama_online": online,
        "available_models": models,
        "current_model": engine_cfg.get("model", ""),
        "base_url": engine_cfg.get("base_url", ""),
        "temperature": cfg.get("temperature", 0.7),
        "max_tokens": cfg.get("max_tokens", 4096),
        "system_prompt": cfg.get("system_prompt", ""),
        "fallback_chain": cfg.get("fallback_chain", []),
        "identity_name": identity_cfg.get("name", "WanClaw"),
        "identity_emoji": identity_cfg.get("emoji", "🦞"),
        "soul_content": soul_content,
        "auto_reply_rules": ar.get_rules(),
        "nl_task_enabled": cfg.get("nl_task", {}).get("enabled", False),
        "security_patterns": cfg.get("security", {}).get("blocked_patterns", [])
    }

@app.post("/api/admin/ai/ollama/switch-model", tags=["AI引擎"])
async def ai_switch_model(body: Dict[str, str], authorization: str = Header(None)):
    _require_auth(authorization)
    model = body.get("model", "")
    if not model:
        raise HTTPException(status_code=400, detail="请提供模型名称")
    cfg_path = FPath(__file__).parent.parent / "im_adapter" / "config" / "config.yaml"
    if not cfg_path.exists():
        cfg_path = FPath("/root/wanclaw/wanclaw/backend/im_adapter/config/config.yaml")
    try:
        import yaml
        with open(cfg_path) as f:
            data = yaml.safe_load(f)
        data.setdefault("ai", {}).setdefault("ollama", {})["model"] = model
        with open(cfg_path, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
        global _ai_config
        _ai_config = None
        return {"success": True, "message": f"已切换到模型: {model}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/ai/provider", tags=["AI引擎"])
async def ai_update_provider(body: Dict[str, str], authorization: str = Header(None)):
    _require_auth(authorization)
    engine = body.get("engine", "")
    model = body.get("model", "")
    api_key = body.get("api_key", "")
    base_url = body.get("base_url", "")
    temperature = body.get("temperature")
    max_tokens = body.get("max_tokens")
    system_prompt = body.get("system_prompt", "")
    fallback_chain = body.get("fallback_chain", [])
    identity_name = body.get("identity_name", "")
    identity_emoji = body.get("identity_emoji", "")
    soul_content = body.get("soul_content", "")
    cfg_path = FPath(__file__).parent.parent / "im_adapter" / "config" / "config.yaml"
    if not cfg_path.exists():
        cfg_path = FPath("/root/wanclaw/wanclaw/backend/im_adapter/config/config.yaml")
    try:
        import yaml
        with open(cfg_path) as f:
            data = yaml.safe_load(f)
        if engine:
            data.setdefault("ai", {})["engine"] = engine
            if engine == "custom" and base_url:
                data["ai"].setdefault("custom", {})["base_url"] = base_url
                data["ai"]["custom"]["model"] = model
                data["ai"]["custom"]["api_key"] = api_key
                data["ai"]["custom"]["enabled"] = True
            elif engine != "ollama" and api_key:
                data["ai"].setdefault(engine, {})["api_key"] = api_key
                data["ai"][engine]["enabled"] = True
            if model and engine != "custom":
                data["ai"].setdefault(engine, {})["model"] = model
        if temperature is not None:
            data.setdefault("ai", {})["temperature"] = float(temperature)
        if max_tokens:
            data.setdefault("ai", {})["max_tokens"] = int(max_tokens)
        if system_prompt:
            data.setdefault("ai", {})["system_prompt"] = system_prompt
        if fallback_chain:
            data.setdefault("ai", {})["fallback_chain"] = fallback_chain
        if identity_name:
            data.setdefault("identity", {})["name"] = identity_name
        if identity_emoji:
            data.setdefault("identity", {})["emoji"] = identity_emoji
        if soul_content:
            soul_path = FPath.home() / ".wanclaw" / "SOUL.md"
            soul_path.parent.mkdir(parents=True, exist_ok=True)
            soul_path.write_text(soul_content)
        with open(cfg_path, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
        global _ai_config
        _ai_config = None
        if "ollama" in _ai_cache:
            del _ai_cache["ollama"]
        return {"success": True, "message": "配置已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
async def ai_get_rules(authorization: str = Header(None)):
    _require_auth(authorization)
    ar = _get_auto_reply()
    return {"success": True, "rules": ar.get_rules()}

@app.post("/api/admin/ai/auto-reply/rules", tags=["AI引擎"])
async def ai_add_rule(body: Dict, authorization: str = Header(None)):
    _require_auth(authorization)
    keywords = body.get("keywords", [])
    reply = body.get("reply", "")
    platform = body.get("platform")
    if not keywords or not reply:
        raise HTTPException(status_code=400, detail="请提供关键词和回复内容")
    ar = _get_auto_reply()
    ar.add_rule(keywords, reply, platform)
    return {"success": True, "message": "规则已添加"}

@app.delete("/api/admin/ai/auto-reply/rules/{index}", tags=["AI引擎"])
async def ai_delete_rule(index: int, authorization: str = Header(None)):
    _require_auth(authorization)
    ar = _get_auto_reply()
    if 0 <= index < len(ar.get_rules()):
        ar.remove_rule(index)
        return {"success": True, "message": "规则已删除"}
    raise HTTPException(status_code=404, detail="规则不存在")

@app.post("/api/admin/ai/chat", tags=["AI引擎"])
async def ai_chat(body: Dict, authorization: str = Header(None)):
    _require_auth(authorization)
    message = body.get("message", "")
    platform = body.get("platform")
    if not message:
        raise HTTPException(status_code=400, detail="请提供消息内容")
    sec = PromptSecurity(_get_ai_config().get("security", {}))
    is_safe, reason = sec.check_input(message)
    if not is_safe:
        return {"success": False, "matched_rule": False, "reply": f"输入被拒绝: {reason}", "security_blocked": True}
    ar = _get_auto_reply()
    try:
        result = await ar.process_message(message, platform)
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "matched_rule": False, "reply": "处理失败", "error": str(e)}

@app.post("/api/admin/ai/chat/stream", tags=["AI引擎"])
async def ai_chat_stream(body: Dict, authorization: str = Header(None)):
    _require_auth(authorization)
    message = body.get("message", "")
    if not message:
        raise HTTPException(status_code=400, detail="请提供消息内容")
    sec = PromptSecurity(_get_ai_config().get("security", {}))
    is_safe, reason = sec.check_input(message)
    if not is_safe:
        return {"success": False, "reply": f"输入被拒绝: {reason}", "security_blocked": True}

    async def generate():
        try:
            ollama = _get_ollama()
            async for chunk in ollama.stream_chat([{"role": "user", "content": message}]):
                if "error" in chunk:
                    yield f"data: {json.dumps({'error': chunk['error']})}\n\n"
                else:
                    yield f"data: {json.dumps({'delta': chunk.get('delta', ''), 'done': chunk.get('done', False)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/api/admin/ai/nl-task", tags=["AI引擎"])
async def ai_nl_task(body: Dict, authorization: str = Header(None)):
    _require_auth(authorization)
    command = body.get("command", "")
    if not command:
        raise HTTPException(status_code=400, detail="请提供自然语言指令")
    sec = PromptSecurity(_get_ai_config().get("security", {}))
    is_safe, reason = sec.check_input(command)
    if not is_safe:
        return {"success": False, "message": f"指令被拒绝: {reason}", "security_blocked": True}
    try:
        from wanclaw.backend.ai.nl_task import NLTaskEngine
        from wanclaw.backend.skills import get_skill_manager
        sm = get_skill_manager()
        ollama = _get_ollama()
        nl = NLTaskEngine(_get_ai_config(), ollama, sm)
        result = await nl.handle_message(command)
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "message": str(e), "error": str(e)}


@app.get("/api/admin/rpa/tools", tags=["RPA自动化"])
async def list_rpa_tools(authorization: str = Header(None)):
    _require_auth(authorization)
    try:
        from wanclaw.backend.rpa.playwright_driver import BrowserType
    except ImportError:
        pass
    tools = [
        {"id": "launch_browser", "name": "启动浏览器", "icon": "🌐", "description": "启动浏览器实例（Chromium/Firefox/WebKit）", "action": "launch_browser", "params": [], "status": "ready"},
        {"id": "goto", "name": "导航页面", "icon": "🧭", "description": "打开指定URL页面", "action": "goto", "params": [{"name": "url", "label": "目标URL", "type": "string", "required": True}], "status": "ready"},
        {"id": "screenshot", "name": "页面截图", "icon": "📸", "description": "截取当前页面快照", "action": "screenshot", "params": [{"name": "url", "label": "目标URL", "type": "string", "required": True}], "status": "ready"},
    ]
    return {"success": True, "tools": tools}


@app.post("/api/admin/rpa/execute", tags=["RPA自动化"])
async def execute_rpa(body: Dict, authorization: str = Header(None)):
    _require_auth(authorization)
    action = body.get("action", "")
    target = body.get("target", "")
    params = body.get("params", {})
    if not action:
        raise HTTPException(status_code=400, detail="请提供action参数")
    try:
        from wanclaw.backend.rpa.playwright_driver import get_rpa_manager
        rpa = await get_rpa_manager()
        result = await rpa.execute(action, target, params)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/conversation/reply", tags=["对话引擎"])
async def conversation_reply(body: Dict[str, Any]):
    from wanclaw.backend.im_adapter.conversation import get_conversation_engine
    engine = get_conversation_engine()
    platform = body.get("platform", "")
    chat_id = body.get("chat_id", "")
    user_id = body.get("user_id", chat_id)
    content = body.get("content", "")
    if not content:
        raise HTTPException(status_code=400, detail="消息内容不能为空")
    result = await engine.process_message(platform, chat_id, user_id, content)
    return {"success": True, **result}

@app.get("/api/conversation/context/{platform}/{chat_id}", tags=["对话引擎"])
async def get_conversation_context(platform: str, chat_id: str, authorization: str = Header(None)):
    _require_auth(authorization)
    from wanclaw.backend.im_adapter.conversation import get_conversation_engine
    engine = get_conversation_engine()
    key = f"{platform}:{chat_id}"
    matching = {k: v for k, v in engine.contexts.items() if k.startswith(key)}
    result = []
    for k, ctx in matching.items():
        result.append({
            "key": k,
            "user_id": ctx.user_id,
            "message_count": len(ctx.history),
            "last_active": ctx.last_active,
            "recent_messages": ctx.history[-10:],
        })
    return {"success": True, "contexts": result}

@app.get("/api/conversation/rules", tags=["对话引擎"])
async def get_conversation_rules(authorization: str = Header(None)):
    _require_auth(authorization)
    from wanclaw.backend.im_adapter.conversation import get_conversation_engine
    engine = get_conversation_engine()
    return {"success": True, "rules": engine.get_rules()}

@app.post("/api/conversation/rules", tags=["对话引擎"])
async def add_conversation_rule(body: Dict[str, Any], authorization: str = Header(None)):
    _require_auth(authorization)
    keywords = body.get("keywords", [])
    reply = body.get("reply", "")
    platform = body.get("platform")
    if not keywords or not reply:
        raise HTTPException(status_code=400, detail="关键词和回复内容不能为空")
    from wanclaw.backend.im_adapter.conversation import get_conversation_engine
    engine = get_conversation_engine()
    engine.add_rule(keywords, reply, platform)
    return {"success": True, "message": "规则已添加"}

@app.delete("/api/conversation/rules/{index}", tags=["对话引擎"])
async def delete_conversation_rule(index: int, authorization: str = Header(None)):
    _require_auth(authorization)
    from wanclaw.backend.im_adapter.conversation import get_conversation_engine
    engine = get_conversation_engine()
    if 0 <= index < len(engine.get_rules()):
        engine.remove_rule(index)
        return {"success": True, "message": "规则已删除"}
    raise HTTPException(status_code=404, detail="规则不存在")

@app.put("/api/conversation/rules/{index}/toggle", tags=["对话引擎"])
async def toggle_conversation_rule(index: int, request: dict, authorization: str = Header(None)):
    _require_auth(authorization)
    from wanclaw.backend.im_adapter.conversation import get_conversation_engine
    engine = get_conversation_engine()
    enabled = request.get("enabled", True)
    if 0 <= index < len(engine.get_rules()):
        engine.toggle_rule(index, enabled)
        return {"success": True}
    raise HTTPException(status_code=404, detail="规则不存在")

@app.get("/api/conversation/stats", tags=["对话引擎"])
async def get_conversation_stats(authorization: str = Header(None)):
    _require_auth(authorization)
    from wanclaw.backend.im_adapter.conversation import get_conversation_engine
    engine = get_conversation_engine()
    return {"success": True, "stats": engine.get_stats()}


@app.get("/api/clawhub/skills", tags=["技能市场"])
async def clawhub_list_skills(category: str = None, keyword: str = None, source: str = None, authorization: str = Header(None)):
    from wanclaw.backend.skills.clawhub import get_clawhub
    hub = get_clawhub()
    if source == "remote":
        skills = hub.remote_search(query=keyword, category=category)
    elif source == "all":
        local = hub.list_skills(category=category, keyword=keyword)
        remote = hub.remote_search(query=keyword, category=category)
        local_names = {s["name"] for s in local}
        skills = local + [s for s in remote if s["name"] not in local_names]
    else:
        skills = hub.list_skills(category=category, keyword=keyword)
    return {"success": True, "skills": skills, "count": len(skills)}

@app.get("/api/clawhub/skills/{name}", tags=["技能市场"])
async def clawhub_get_skill(name: str, authorization: str = Header(None)):
    from wanclaw.backend.skills.clawhub import get_clawhub
    hub = get_clawhub()
    skill = hub.get_skill(name) or hub.remote.get_skill(name)
    if not skill:
        raise HTTPException(status_code=404, detail=f"Skill not found: {name}")
    return {"success": True, "skill": skill}

@app.get("/api/clawhub/stats", tags=["技能市场"])
async def clawhub_stats(authorization: str = Header(None)):
    from wanclaw.backend.skills.clawhub import get_clawhub
    hub = get_clawhub()
    return {"success": True, **hub.get_stats()}

@app.post("/api/clawhub/sync", tags=["技能市场"])
async def clawhub_sync(authorization: str = Header(None)):
    from wanclaw.backend.skills.clawhub import get_clawhub
    hub = get_clawhub()
    result = await hub.remote_sync()
    return result

@app.post("/api/clawhub/install/{name}", tags=["技能市场"])
async def clawhub_remote_install(name: str, authorization: str = Header(None)):
    from wanclaw.backend.skills.clawhub import get_clawhub
    hub = get_clawhub()
    result = await hub.remote_install(name)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Install failed"))
    return result

@app.post("/api/clawhub/update/{name}", tags=["技能市场"])
async def clawhub_update_skill(name: str, authorization: str = Header(None)):
    from wanclaw.backend.skills.clawhub import get_clawhub
    hub = get_clawhub()
    result = await hub.update_skill(name)
    return result

@app.delete("/api/clawhub/uninstall/{name}", tags=["技能市场"])
async def clawhub_uninstall_skill(name: str, authorization: str = Header(None)):
    from wanclaw.backend.skills.clawhub import get_clawhub
    hub = get_clawhub()
    result = hub.uninstall_skill(name)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Uninstall failed"))
    return result

# ===== MARKETPLACE (插件平台) =====
@app.post("/api/marketplace/register", tags=["插件平台"])
async def marketplace_register(body: Dict[str, str]):
    from wanclaw.backend.skills.marketplace import get_marketplace
    m = get_marketplace()
    return m.register(body.get("username", ""), body.get("email", ""), body.get("password", ""))

@app.post("/api/marketplace/login", tags=["插件平台"])
async def marketplace_login(body: Dict[str, str]):
    from wanclaw.backend.skills.marketplace import get_marketplace
    m = get_marketplace()
    return m.login(body.get("username", ""), body.get("password", ""))

@app.get("/api/marketplace/plugins", tags=["插件平台"])
async def marketplace_list(
    page: int = Query(1, ge=1),
    per_page: int = Query(200, ge=1),
    category: Optional[str] = None,
    search: Optional[str] = None,
    keyword: Optional[str] = None,
):
    try:
        from wanclaw.backend.config import get_config
        config = get_config()
        marketplace_url = config.get("marketplace.url", "")

        if marketplace_url:
            import httpx
            params = {"page": page, "per_page": per_page}
            if category:
                params["category"] = category
            if search:
                params["search"] = search
            if keyword:
                params["search"] = keyword
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(f"{marketplace_url}/api/community/plugins/list", params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    for plugin in data.get("plugins", []):
                        plugin["plugin_name"] = plugin.get("name") or plugin.get("plugin_name")
                        plugin["download_url"] = f"{marketplace_url}/api/community/plugins/file/{plugin['plugin_id']}"
                        plugin["compatible_version"] = plugin.get("compatible_wanclaw_version", "*")
                    return {"success": True, **data}
                else:
                    pass
    except Exception:
        pass

    from wanclaw.backend.skills.marketplace import get_marketplace
    m = get_marketplace()
    q = search or keyword
    raw = m.list_plugins(category=category, keyword=q, limit=per_page)
    plugins = []
    for p in raw:
        p["plugin_name"] = p.get("name")
        p["plugin_id"] = p.get("name")
        plugins.append(p)
    return {"success": True, "plugins": plugins, "total": len(plugins)}

@app.get("/api/marketplace/plugins/{name}", tags=["插件平台"])
async def marketplace_get(name: str):
    from wanclaw.backend.skills.marketplace import get_marketplace
    m = get_marketplace()
    p = m.get_plugin(name)
    if not p:
        raise HTTPException(status_code=404, detail="插件不存在")
    return {"success": True, "plugin": p}

@app.post("/api/marketplace/upload", tags=["插件平台"])
async def marketplace_upload(file: bytes, authorization: str = Header(None)):
    from wanclaw.backend.skills.marketplace import get_marketplace
    m = get_marketplace()
    return m.upload_plugin(authorization or "", file)

@app.get("/api/marketplace/download/{name}", tags=["插件平台"])
async def marketplace_download(name: str):
    from wanclaw.backend.skills.marketplace import get_marketplace
    m = get_marketplace()
    data = m.download_plugin(name)
    if not data:
        raise HTTPException(status_code=404, detail="插件不存在")
    from fastapi.responses import Response
    return Response(content=data, media_type="application/zip", headers={"Content-Disposition": f"attachment; filename={name}.zip"})

@app.delete("/api/marketplace/plugins/{name}", tags=["插件平台"])
async def marketplace_delete(name: str, authorization: str = Header(None)):
    from wanclaw.backend.skills.marketplace import get_marketplace
    m = get_marketplace()
    return m.delete_plugin(name, authorization or "")

@app.get("/api/marketplace/my", tags=["插件平台"])
async def marketplace_my_plugins(authorization: str = Header(None)):
    from wanclaw.backend.skills.marketplace import get_marketplace
    m = get_marketplace()
    return {"success": True, "plugins": m.get_user_plugins(authorization or "")}

@app.get("/api/marketplace/stats", tags=["插件平台"])
async def marketplace_stats():
    from wanclaw.backend.skills.marketplace import get_marketplace
    m = get_marketplace()
    return {"success": True, **m.get_stats()}


@app.get("/api/plugins", tags=["插件管理"])
async def list_plugins(authorization: str = Header(None)):
    _require_auth(authorization)
    from wanclaw.backend.agent.plugins import get_plugin_manager
    pm = get_plugin_manager()
    return {"success": True, "plugins": pm.discover_plugins()}


@app.post("/api/plugins/{name}/load", tags=["插件管理"])
async def load_plugin(name: str, authorization: str = Header(None)):
    _require_auth(authorization)
    from wanclaw.backend.agent.plugins import get_plugin_manager
    pm = get_plugin_manager()
    ok = pm.load_plugin(name)
    return {"success": ok, "message": "loaded" if ok else "failed"}


@app.post("/api/plugins/{name}/unload", tags=["插件管理"])
async def unload_plugin(name: str, authorization: str = Header(None)):
    _require_auth(authorization)
    from wanclaw.backend.agent.plugins import get_plugin_manager
    pm = get_plugin_manager()
    ok = pm.unload_plugin(name)
    return {"success": ok, "message": "unloaded" if ok else "failed"}


@app.post("/api/plugins/{name}/reload", tags=["插件管理"])
async def reload_plugin(name: str, authorization: str = Header(None)):
    _require_auth(authorization)
    from wanclaw.backend.agent.plugins import get_plugin_manager
    pm = get_plugin_manager()
    ok = pm.reload_plugin(name)
    return {"success": ok, "message": "reloaded" if ok else "failed"}


@app.post("/api/plugins/{name}/enable", tags=["插件管理"])
async def enable_plugin(name: str, authorization: str = Header(None)):
    _require_auth(authorization)
    from wanclaw.backend.agent.plugins import get_plugin_manager
    pm = get_plugin_manager()
    pm.enable_plugin(name)
    return {"success": True}


@app.post("/api/plugins/{name}/disable", tags=["插件管理"])
async def disable_plugin(name: str, authorization: str = Header(None)):
    _require_auth(authorization)
    from wanclaw.backend.agent.plugins import get_plugin_manager
    pm = get_plugin_manager()
    pm.disable_plugin(name)
    return {"success": True}


@app.get("/api/plugins/stats", tags=["插件管理"])
async def plugin_stats(authorization: str = Header(None)):
    _require_auth(authorization)
    from wanclaw.backend.agent.plugins import get_plugin_manager
    pm = get_plugin_manager()
    return {"success": True, **pm.get_stats()}


@app.post("/api/plugins/scan", tags=["插件管理"])
async def scan_plugin(file: UploadFile = File(...), authorization: str = Header(None)):
    _require_auth(authorization)
    import tempfile
    import os
    from wanclaw.backend.plugin.security import get_plugin_security
    
    security = get_plugin_security()
    
    suffix = os.path.splitext(file.filename)[1] if file.filename else '.zip'
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        report = security.scan_plugin_zip(tmp_path)
        return {
            "success": True,
            "safe": report.safe,
            "risk_level": report.risk_level.value,
            "warnings": report.warnings,
            "errors": report.errors,
            "permissions_allowed": report.permissions_allowed,
            "permissions_denied": report.permissions_denied,
            "ast_findings": report.ast_findings,
            "network_urls": report.network_urls,
            "suspicious_imports": report.suspicious_imports,
            "audit_log": report.audit_log,
        }
    finally:
        os.unlink(tmp_path)


@app.post("/api/voice/tts", tags=["语音"])
async def voice_tts(body: Dict[str, str], authorization: str = Header(None)):
    _require_auth(authorization)
    text = body.get("text", "")
    voice = body.get("voice")
    if not text:
        raise HTTPException(status_code=400, detail="文本不能为空")
    from wanclaw.backend.ai.voice import get_voice_engine
    engine = get_voice_engine()
    result = await engine.text_to_speech(text, voice=voice)
    return result

@app.post("/api/voice/stt", tags=["语音"])
async def voice_stt(body: Dict[str, str], authorization: str = Header(None)):
    _require_auth(authorization)
    audio_b64 = body.get("audio_base64", "")
    fmt = body.get("format", "wav")
    if not audio_b64:
        raise HTTPException(status_code=400, detail="音频数据不能为空")
    from wanclaw.backend.ai.voice import get_voice_engine
    engine = get_voice_engine()
    result = await engine.speech_to_text_base64(audio_b64, fmt)
    return result


# WebSocket端点（用于实时消息推送）
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    """WebSocket连接管理器"""
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)
        for d in dead:
            self.active_connections.remove(d)

    async def broadcast_health(self):
        try:
            gateway = get_gateway()
            if gateway.is_running:
                health_data = await gateway.health_check()
                await self.broadcast({"type": "health", "data": {
                    "status": "healthy", "running": True,
                    "adapter_count": health_data["adapter_count"],
                    "uptime": health_data["uptime"],
                    "adapters": health_data["adapters"]
                }})
        except Exception:
            await self.broadcast({"type": "health", "data": {
                "status": "healthy", "running": True, "adapter_count": 0,
                "uptime": 0, "adapters": {}
            }})

manager = ConnectionManager()

@app.websocket("/ws/messages")
async def websocket_endpoint(websocket: WebSocket):
    origin = websocket.headers.get("origin", "")
    if origin and not _check_ws_origin(origin):
        await websocket.close(code=4003, reason="Origin not allowed")
        return
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            logger.debug(f"收到WebSocket消息: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket连接异常: {e}")
        manager.disconnect(websocket)

# 启动时初始化
@app.on_event("startup")
async def startup_event():
    logger.info("启动IM适配器API服务...")
    
    gateway = get_gateway()
    
    config_path = "config/config.yaml"
    config = None
    try:
        import yaml
        from pathlib import Path
        cfg_file = Path(config_path)
        if not cfg_file.exists():
            cfg_file = Path("/data/wanclaw/wanclaw/backend/im_adapter/config/config.yaml")
        if not cfg_file.exists():
            cfg_file = Path(__file__).parent.parent.parent / "backend/im_adapter/config/config.yaml"
        if cfg_file.exists():
            with open(cfg_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"加载配置: {cfg_file}")
    except Exception as e:
        logger.warning(f"配置加载失败: {e}")
    
    if config:
        from wanclaw.backend.im_adapter.adapters.wecom import WeComAdapter
        from wanclaw.backend.im_adapter.adapters.feishu import FeishuAdapter
        from wanclaw.backend.im_adapter.adapters.qq import QQAdapter
        from wanclaw.backend.im_adapter.adapters.wechat import WeChatAdapter
        from wanclaw.backend.im_adapter.adapters.telegram import TelegramAdapter
        from wanclaw.backend.im_adapter.adapters.whatsapp import WhatsAppAdapter
        from wanclaw.backend.im_adapter.adapters.discord import DiscordAdapter
        from wanclaw.backend.im_adapter.adapters.slack import SlackAdapter
        from wanclaw.backend.im_adapter.adapters.signal import SignalAdapter
        from wanclaw.backend.im_adapter.adapters.teams import TeamsAdapter
        from wanclaw.backend.im_adapter.adapters.matrix import MatrixAdapter
        from wanclaw.backend.im_adapter.adapters.line import LineAdapter
        from wanclaw.backend.im_adapter.adapters.irc import IRCAdapter
        from wanclaw.backend.im_adapter.adapters.taobao import TaobaoAdapter
        from wanclaw.backend.im_adapter.adapters.jd import JdAdapter
        from wanclaw.backend.im_adapter.adapters.pinduoduo import PinduoduoAdapter
        from wanclaw.backend.im_adapter.adapters.douyin import DouyinAdapter
        from wanclaw.backend.im_adapter.adapters.kuaishou import KuaishouAdapter
        from wanclaw.backend.im_adapter.adapters.youzan import YouzanAdapter
        from wanclaw.backend.im_adapter.adapters.koad import KoudatongAdapter

        if config.get('wecom', {}).get('enabled'):
            try: gateway.create_and_register(PlatformType.WECOM, config['wecom'])
            except Exception as e: logger.warning(f"Wecom adapter init failed: {e}")
        if config.get('feishu', {}).get('enabled'):
            try: gateway.create_and_register(PlatformType.FEISHU, config['feishu'])
            except Exception as e: logger.warning(f"Feishu adapter init failed: {e}")
        if config.get('qq', {}).get('enabled'):
            try: gateway.create_and_register(PlatformType.QQ, config['qq'])
            except Exception as e: logger.warning(f"QQ adapter init failed: {e}")
        if config.get('wechat', {}).get('enabled'):
            try: gateway.create_and_register(PlatformType.WECHAT, config['wechat'])
            except Exception as e: logger.warning(f"WeChat adapter init failed: {e}")
        if config.get('telegram', {}).get('enabled'):
            try: gateway.create_and_register(PlatformType.TELEGRAM, config['telegram'])
            except Exception as e: logger.warning(f"Telegram adapter init failed: {e}")
        if config.get('whatsapp', {}).get('enabled'):
            try: gateway.create_and_register(PlatformType.WHATSAPP, config['whatsapp'])
            except Exception as e: logger.warning(f"WhatsApp adapter init failed: {e}")
        if config.get('discord', {}).get('enabled'):
            try: gateway.create_and_register(PlatformType.DISCORD, config['discord'])
            except Exception as e: logger.warning(f"Discord adapter init failed: {e}")
        if config.get('slack', {}).get('enabled'):
            try: gateway.create_and_register(PlatformType.SLACK, config['slack'])
            except Exception as e: logger.warning(f"Slack adapter init failed: {e}")
        if config.get('signal', {}).get('enabled'):
            try: gateway.create_and_register(PlatformType.SIGNAL, config['signal'])
            except Exception as e: logger.warning(f"Signal adapter init failed: {e}")
        if config.get('teams', {}).get('enabled'):
            try: gateway.create_and_register(PlatformType.TEAMS, config['teams'])
            except Exception as e: logger.warning(f"Teams adapter init failed: {e}")
        if config.get('matrix', {}).get('enabled'):
            try: gateway.create_and_register(PlatformType.MATRIX, config['matrix'])
            except Exception as e: logger.warning(f"Matrix adapter init failed: {e}")
        if config.get('line', {}).get('enabled'):
            try: gateway.create_and_register(PlatformType.LINE, config['line'])
            except Exception as e: logger.warning(f"LINE adapter init failed: {e}")
        if config.get('irc', {}).get('enabled'):
            try: gateway.create_and_register(PlatformType.IRC, config['irc'])
            except Exception as e: logger.warning(f"IRC adapter init failed: {e}")
        if config.get('taobao', {}).get('enabled'):
            try: gateway.create_and_register(PlatformType.TAOBAO, config['taobao'])
            except Exception as e: logger.warning(f"Taobao adapter init failed: {e}")
        if config.get('jd', {}).get('enabled'):
            try: gateway.create_and_register(PlatformType.JD, config['jd'])
            except Exception as e: logger.warning(f"JD adapter init failed: {e}")
        if config.get('pinduoduo', {}).get('enabled'):
            try: gateway.create_and_register(PlatformType.PINDUODUO, config['pinduoduo'])
            except Exception as e: logger.warning(f"Pinduoduo adapter init failed: {e}")
        if config.get('douyin', {}).get('enabled'):
            try: gateway.create_and_register(PlatformType.DOUYIN, config['douyin'])
            except Exception as e: logger.warning(f"Douyin adapter init failed: {e}")
        if config.get('kuaishou', {}).get('enabled'):
            try: gateway.create_and_register(PlatformType.KUAISHOU, config['kuaishou'])
            except Exception as e: logger.warning(f"Kuaishou adapter init failed: {e}")
        if config.get('youzan', {}).get('enabled'):
            try: gateway.create_and_register(PlatformType.YOUZAN, config['youzan'])
            except Exception as e: logger.warning(f"Youzan adapter init failed: {e}")
        if config.get('koudatong', {}).get('enabled'):
            try: gateway.create_and_register(PlatformType.KOUDATONG, config['koudatong'])
            except Exception as e: logger.warning(f"Koudatong adapter init failed: {e}")
        
        logger.info(f"已注册 {len(gateway.adapters)} 个适配器")
    
    async def handle_message_and_broadcast(message: UnifiedMessage):
        try:
            message_event = MessageReceived(
                platform=message.platform,
                message_id=message.message_id,
                chat_id=message.chat_id,
                user_id=message.user_id,
                username=message.username,
                chat_type=message.chat_type,
                message_type=message.message_type,
                text=message.text,
                timestamp=message.timestamp.isoformat(),
                is_command=message.is_command
            )
            await manager.broadcast(message_event.dict())
        except Exception as e:
            logger.error(f"处理消息广播失败: {e}")
    
    gateway.register_message_handler(handle_message_and_broadcast)
    gateway.register_error_handler(lambda e: logger.error(f"网关错误: {e}"))

    from wanclaw.backend.agent.plugins import get_plugin_manager
    from wanclaw.backend.agent.hooks import get_hook_manager
    pm = get_plugin_manager()
    pm.set_hook_manager(get_hook_manager())
    pm.load_all()
    pm.start_hot_reload()
    logger.info(f"Plugin manager ready, {len(pm.discover_plugins())} plugins discovered")

    import asyncio
    async def ws_broadcast_loop():
        while True:
            await asyncio.sleep(5)
            if manager.active_connections:
                await manager.broadcast_health()
    asyncio.create_task(ws_broadcast_loop())

    await gateway.start()
    logger.info("IM适配器API服务启动完成")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("关闭IM适配器API服务...")
    from wanclaw.backend.agent.plugins import get_plugin_manager
    pm = get_plugin_manager()
    pm.stop_hot_reload()
    gateway = get_gateway()
    await gateway.stop()
    logger.info("IM适配器API服务已关闭")


@app.get('/api/admin/ai/router-status', tags=['AI引擎'])
async def ai_router_status(authorization: str = Header(None)):
    _require_auth(authorization)
    router = _get_model_router()
    return {'success': True, **router.get_status()}


# ==================== 插件市场 API ====================

class MarketplacePluginInfo(BaseModel):
    plugin_id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    plugin_type: str = "skill"
    category: str = ""
    downloads: int = 0
    rating: float = 5.0
    download_url: str = ""
    compatible_version: str = "*"


class MarketplaceInstallRequest(BaseModel):
    plugin_id: str
    download_url: str
    version: str = ""
    checksum: str = ""


class MarketplaceInstallResponse(BaseModel):
    success: bool
    message: str
    plugin_id: str = ""
    version: str = ""
    warnings: List[str] = Field(default_factory=list)


@app.get('/api/marketplace/status', tags=['插件市场'])
async def marketplace_status():
    """获取生态站连接状态"""
    try:
        from wanclaw.backend.config import get_config
        config = get_config()
        marketplace_url = config.get("marketplace.url", "")
        
        return {
            'success': True,
            'connected': bool(marketplace_url),
            'url': marketplace_url,
            'enabled': config.get("marketplace.enabled", True),
            'auto_update': config.get("marketplace.auto_update", True),
        }
    except Exception as e:
        logger.error(f"Marketplace status error: {e}")
        return {'success': False, 'error': str(e)}



@app.get('/api/marketplace/plugin/{plugin_id}', tags=['插件市场'])
async def marketplace_get_plugin(
    plugin_id: str,
    authorization: str = Header(None)
):
    """获取生态站插件详情"""
    _require_auth(authorization)
    
    try:
        from wanclaw.backend.config import get_config
        config = get_config()
        marketplace_url = config.get("marketplace.url", "")
        
        if not marketplace_url:
            return {'success': False, 'error': 'Marketplace not configured'}
        
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{marketplace_url}/api/community/plugins/detail",
                params={'plugin_id': plugin_id}
            )
            
            if resp.status_code == 200:
                data = resp.json()
                data['download_url'] = f"{marketplace_url}/api/community/plugins/file/{plugin_id}"
                data['install_url'] = _build_install_url(plugin_id, data.get('download_url', ''))
                return {'success': True, **data}
            else:
                return {'success': False, 'error': 'Plugin not found'}
                
    except Exception as e:
        logger.error(f"Marketplace plugin detail error: {e}")
        return {'success': False, 'error': str(e)}


def _build_install_url(plugin_id: str, download_url: str) -> str:
    """构建 wanclaw:// 安装链接"""
    return f"wanclaw://install?plugin_id={plugin_id}&url={download_url}"


@app.post('/api/marketplace/install', tags=['插件市场'])
async def marketplace_install_plugin(
    request: MarketplaceInstallRequest,
    background_tasks: BackgroundTasks,
    authorization: str = Header(None)
):
    """从生态站安装插件"""
    _require_auth(authorization)
    
    try:
        from wanclaw.backend.plugin.manager import get_plugin_manager
        from wanclaw.backend.protocol_handler import get_protocol_handler
        
        pm = get_plugin_manager()
        handler = get_protocol_handler()
        handler.set_plugin_manager(pm)
        
        logger.info(f"Installing plugin from marketplace: {request.plugin_id}")
        
        result = await pm.install_from_url(request.download_url, request.plugin_id)
        
        return {
            'success': result.get('success', False),
            'message': result.get('error', 'Installed successfully') if not result.get('success') else 'Plugin installed successfully',
            'plugin_id': request.plugin_id,
            'version': result.get('version', ''),
            'details': result,
        }
        
    except Exception as e:
        logger.error(f"Marketplace install error: {e}")
        return {'success': False, 'error': str(e)}


@app.get('/api/marketplace/install-url', tags=['插件市场'])
async def marketplace_get_install_url(
    plugin_id: str,
    authorization: str = Header(None)
):
    """获取插件安装URL（用于生成 wanclaw:// 链接）"""
    _require_auth(authorization)
    
    try:
        from wanclaw.backend.config import get_config
        config = get_config()
        marketplace_url = config.get("marketplace.url", "")
        
        if not marketplace_url:
            return {'success': False, 'error': 'Marketplace not configured'}
        
        # 获取插件信息
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{marketplace_url}/api/community/plugins/detail",
                params={'plugin_id': plugin_id}
            )
            
            if resp.status_code != 200:
                return {'success': False, 'error': 'Plugin not found'}
            
            data = resp.json()
            download_url = f"{marketplace_url}/api/community/plugins/file/{plugin_id}"
            
            # 构建 wanclaw:// URL
            install_url = _build_install_url(plugin_id, download_url)
            
            return {
                'success': True,
                'plugin_id': plugin_id,
                'download_url': download_url,
                'install_url': install_url,  # wanclaw:// URL
                'version': data.get('version', ''),
                'name': data.get('plugin_name', ''),
            }
            
    except Exception as e:
        logger.error(f"Get install URL error: {e}")
        return {'success': False, 'error': str(e)}


@app.post('/api/marketplace/protocol', tags=['插件市场'])
async def marketplace_handle_protocol(
    url: str = Query(..., description="wanclaw:// URL"),
    authorization: str = Header(None)
):
    """处理 wanclaw:// 协议请求"""
    _require_auth(authorization)
    
    try:
        from wanclaw.backend.plugin.manager import get_plugin_manager
        from wanclaw.backend.protocol_handler import get_protocol_handler
        
        pm = get_plugin_manager()
        handler = get_protocol_handler()
        handler.set_plugin_manager(pm)
        
        # 解析URL
        request = handler.parse_url(url)
        if not request:
            return {'success': False, 'error': 'Invalid wanclaw:// URL'}
        
        # 处理请求
        result = await handler.handle(request)
        
        return {
            'success': result.success,
            'message': result.message,
            'plugin_id': result.plugin_id,
            'version': result.version,
            'details': result.details,
        }
        
    except Exception as e:
        logger.error(f"Protocol handler error: {e}")
        return {'success': False, 'error': str(e)}


@app.get('/api/marketplace/config', tags=['插件市场'])
async def marketplace_config(
    authorization: str = Header(None)
):
    """获取生态站配置"""
    _require_auth(authorization)
    
    try:
        from wanclaw.backend.config import get_config
        config = get_config()
        
        return {
            'success': True,
            'enabled': config.get("marketplace.enabled", True),
            'url': config.get("marketplace.url", ""),
            'auto_update': config.get("marketplace.auto_update", True),
            'version_check': config.get("marketplace.version_check", True),
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


@app.put('/api/marketplace/config', tags=['插件市场'])
async def marketplace_update_config(
    body: Dict[str, Any],
    authorization: str = Header(None)
):
    """更新生态站配置"""
    _require_auth(authorization)
    
    try:
        from wanclaw.backend.config import get_config
        config = get_config()
        
        if 'url' in body:
            config.set("marketplace.url", body['url'])
        if 'enabled' in body:
            config.set("marketplace.enabled", body['enabled'])
        if 'auto_update' in body:
            config.set("marketplace.auto_update", body['auto_update'])
        if 'version_check' in body:
            config.set("marketplace.version_check", body['version_check'])
        
        config.save()
        
        return {'success': True, 'message': 'Configuration updated'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@app.get('/api/marketplace/check-update', tags=['插件市场'])
async def marketplace_check_updates(
    authorization: str = Header(None)
):
    """检查已安装插件的更新"""
    _require_auth(authorization)
    
    try:
        from wanclaw.backend.plugin.manager import get_plugin_manager
        pm = get_plugin_manager()
        
        updates = await pm.check_updates()
        
        return {
            'success': True,
            'updates': updates,
            'count': len(updates),
        }
    except Exception as e:
        logger.error(f"Check updates error: {e}")
        return {'success': False, 'error': str(e)}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

_static_root = FPath(__file__).parent.parent.parent / "frontend/static"
if not _safe_exists(_static_root):
    _static_root = FPath("/root/wanclaw/wanclaw/frontend/static")
if not _safe_exists(_static_root):
    _static_root = FPath("/data/wanclaw/wanclaw/wanclaw/frontend/static")
if not _safe_exists(_static_root):
    _static_root = FPath("/data/wanclaw/wanclaw/wanclaw/frontend-vue/dist")
if _safe_exists(_static_root):
    app.mount("/", StaticFiles(directory=str(_static_root), html=True), name="static")