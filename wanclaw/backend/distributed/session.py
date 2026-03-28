"""
WanClaw 分布式平台核心模块
统一会话上下文 - 融合AI会话、任务会话、IM会话
支持跨平台消息同步、上下文共享、节点间迁移
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from .namespace import TenantNamespace
from .state import CentralStateManager, get_central_state

logger = logging.getLogger(__name__)


class SessionType(Enum):
    AI_CONVERSATION = "ai_conversation"
    TASK_SESSION = "task_session"
    IM_SESSION = "im_session"
    MIXED = "mixed"


class SessionStatus(Enum):
    ACTIVE = "active"
    IDLE = "idle"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


@dataclass
class Message:
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UnifiedSession:
    session_id: str
    tenant_id: str
    session_type: SessionType = SessionType.MIXED
    platform: str = ""
    chat_id: str = ""
    user_id: str = ""
    status: SessionStatus = SessionStatus.ACTIVE
    context: Dict[str, Any] = field(default_factory=dict)
    history: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    ttl: int = 3600
    node_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class UnifiedSessionContext:
    """
    统一会话上下文管理器
    - 多平台消息汇聚 (WeChat, WhatsApp, DingTalk...)
    - AI对话上下文 (Ollama, OpenAI, Claude...)
    - 任务执行上下文 (RPA, Workflow, NLTask...)
    - 跨节点状态同步
    """

    def __init__(self, state: CentralStateManager = None):
        self._state = state
        self._sessions: Dict[str, UnifiedSession] = {}
        self._lock = asyncio.Lock()
        self._handlers: Dict[str, List[Callable]] = {}

    async def initialize(self):
        if self._state is None:
            self._state = await get_central_state()

    def _get_session_key(self, session_id: str, tenant_id: str) -> str:
        ns = TenantNamespace(tenant_id)
        return ns.session_key(session_id)

    async def create_session(
        self,
        session_id: str,
        tenant_id: str,
        session_type: SessionType = SessionType.MIXED,
        platform: str = "",
        chat_id: str = "",
        user_id: str = "",
        ttl: int = 3600,
        node_id: str = None,
        metadata: Dict[str, Any] = None,
    ) -> UnifiedSession:
        session = UnifiedSession(
            session_id=session_id,
            tenant_id=tenant_id,
            session_type=session_type,
            platform=platform,
            chat_id=chat_id,
            user_id=user_id,
            ttl=ttl,
            node_id=node_id,
            metadata=metadata or {},
        )
        key = self._get_session_key(session_id, tenant_id)
        await self._state.set_with_version(
            key,
            self._session_to_dict(session),
            tenant_id,
            ttl=ttl,
        )
        async with self._lock:
            self._sessions[f"{tenant_id}:{session_id}"] = session
        logger.info(f"Session created: {session_id} for tenant {tenant_id}")
        return session

    async def get_session(self, session_id: str, tenant_id: str) -> Optional[UnifiedSession]:
        key = self._get_session_key(session_id, tenant_id)
        cache_key = f"{tenant_id}:{session_id}"
        if cache_key in self._sessions:
            return self._sessions[cache_key]
        data, version = await self._state.get_with_version(key, tenant_id)
        if not data:
            return None
        session = self._dict_to_session(data)
        async with self._lock:
            self._sessions[cache_key] = session
        return session

    async def update_session(
        self,
        session_id: str,
        tenant_id: str,
        **kwargs,
    ) -> Optional[UnifiedSession]:
        session = await self.get_session(session_id, tenant_id)
        if not session:
            return None
        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)
        session.updated_at = datetime.now()
        session.last_active = datetime.now()
        key = self._get_session_key(session_id, tenant_id)
        await self._state.set_with_version(
            key,
            self._session_to_dict(session),
            tenant_id,
            ttl=session.ttl,
        )
        return session

    async def add_message(
        self,
        session_id: str,
        tenant_id: str,
        role: str,
        content: str,
        metadata: Dict[str, Any] = None,
    ) -> Optional[UnifiedSession]:
        session = await self.get_session(session_id, tenant_id)
        if not session:
            return None
        msg = Message(role=role, content=content, metadata=metadata or {})
        session.history.append(msg)
        session.last_active = datetime.now()
        session.updated_at = datetime.now()
        max_history = session.metadata.get("max_history", 100)
        if len(session.history) > max_history:
            session.history = session.history[-max_history:]
        key = self._get_session_key(session_id, tenant_id)
        await self._state.set_with_version(
            key,
            self._session_to_dict(session),
            tenant_id,
            ttl=session.ttl,
        )
        return session

    async def get_history(
        self,
        session_id: str,
        tenant_id: str,
        limit: int = 50,
    ) -> List[Message]:
        session = await self.get_session(session_id, tenant_id)
        if not session:
            return []
        return session.history[-limit:]

    async def migrate_session(
        self,
        session_id: str,
        tenant_id: str,
        new_node_id: str,
    ) -> bool:
        session = await self.get_session(session_id, tenant_id)
        if not session:
            return False
        old_node_id = session.node_id
        session.node_id = new_node_id
        session.updated_at = datetime.now()
        key = self._get_session_key(session_id, tenant_id)
        await self._state.set_with_version(
            key,
            self._session_to_dict(session),
            tenant_id,
            ttl=session.ttl,
        )
        await self.publish_session_event(
            tenant_id,
            "session_migrated",
            {
                "session_id": session_id,
                "from_node": old_node_id,
                "to_node": new_node_id,
            },
        )
        logger.info(f"Session {session_id} migrated from {old_node_id} to {new_node_id}")
        return True

    async def suspend_session(self, session_id: str, tenant_id: str) -> bool:
        session = await self.update_session(session_id, tenant_id, status=SessionStatus.SUSPENDED)
        return session is not None

    async def resume_session(self, session_id: str, tenant_id: str) -> bool:
        session = await self.update_session(session_id, tenant_id, status=SessionStatus.ACTIVE)
        return session is not None

    async def terminate_session(self, session_id: str, tenant_id: str) -> bool:
        session = await self.get_session(session_id, tenant_id)
        if not session:
            return False
        session.status = SessionStatus.TERMINATED
        key = self._get_session_key(session_id, tenant_id)
        await self._state.set_with_version(
            key,
            self._session_to_dict(session),
            tenant_id,
            ttl=60,
        )
        cache_key = f"{tenant_id}:{session_id}"
        async with self._lock:
            self._sessions.pop(cache_key, None)
        await self.publish_session_event(tenant_id, "session_terminated", {"session_id": session_id})
        return True

    async def list_sessions(
        self,
        tenant_id: str,
        session_type: SessionType = None,
        status: SessionStatus = None,
        limit: int = 100,
    ) -> List[UnifiedSession]:
        ns = TenantNamespace(tenant_id)
        pattern = ns.key("session:*")
        sessions = []
        async for key in self._state._redis.scan_iter(match=pattern):
            data, _ = await self._state.get_with_version(key.replace(ns.key(""), "").lstrip(":"), tenant_id)
            if data:
                session = self._dict_to_session(data)
                if session_type and session.session_type != session_type:
                    continue
                if status and session.status != status:
                    continue
                sessions.append(session)
        return sorted(sessions, key=lambda s: s.last_active, reverse=True)[:limit]

    async def subscribe_session_events(
        self,
        tenant_id: str,
        handler: Callable[[str, Dict], None],
    ):
        channel = f"session_events_{tenant_id}"
        if channel not in self._handlers:
            self._handlers[channel] = []
        self._handlers[channel].append(handler)
        await self._state.subscribe(channel, handler, tenant_id=None)

    async def publish_session_event(self, tenant_id: str, event_type: str, data: Dict[str, Any]):
        message = {"type": event_type, "tenant_id": tenant_id, "data": data, "timestamp": datetime.now().isoformat()}
        channel = f"session_events_{tenant_id}"
        await self._state.publish(channel, message, tenant_id=None)

    def _session_to_dict(self, session: UnifiedSession) -> Dict[str, Any]:
        return {
            "session_id": session.session_id,
            "tenant_id": session.tenant_id,
            "session_type": session.session_type.value,
            "platform": session.platform,
            "chat_id": session.chat_id,
            "user_id": session.user_id,
            "status": session.status.value,
            "context": session.context,
            "history": [
                {"role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat(), "metadata": m.metadata}
                for m in session.history
            ],
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "last_active": session.last_active.isoformat(),
            "ttl": session.ttl,
            "node_id": session.node_id,
            "metadata": session.metadata,
        }

    def _dict_to_session(self, data: Dict[str, Any]) -> UnifiedSession:
        history = []
        for m in data.get("history", []):
            ts = m.get("timestamp")
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            elif ts is None:
                ts = datetime.now()
            history.append(Message(role=m.get("role", "user"), content=m.get("content", ""), timestamp=ts, metadata=m.get("metadata", {})))
        status_val = data.get("status", "active")
        if isinstance(status_val, str):
            status = SessionStatus(status_val)
        else:
            status = SessionStatus.ACTIVE
        type_val = data.get("session_type", "mixed")
        if isinstance(type_val, str):
            session_type = SessionType(type_val)
        else:
            session_type = SessionType.MIXED
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()
        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        elif updated_at is None:
            updated_at = datetime.now()
        last_active = data.get("last_active")
        if isinstance(last_active, str):
            last_active = datetime.fromisoformat(last_active)
        elif last_active is None:
            last_active = datetime.now()
        return UnifiedSession(
            session_id=data.get("session_id", ""),
            tenant_id=data.get("tenant_id", ""),
            session_type=session_type,
            platform=data.get("platform", ""),
            chat_id=data.get("chat_id", ""),
            user_id=data.get("user_id", ""),
            status=status,
            context=data.get("context", {}),
            history=history,
            created_at=created_at,
            updated_at=updated_at,
            last_active=last_active,
            ttl=data.get("ttl", 3600),
            node_id=data.get("node_id"),
            metadata=data.get("metadata", {}),
        )


_unified_session: Optional[UnifiedSessionContext] = None


async def get_unified_session() -> UnifiedSessionContext:
    global _unified_session
    if _unified_session is None:
        _unified_session = UnifiedSessionContext()
        await _unified_session.initialize()
    return _unified_session
