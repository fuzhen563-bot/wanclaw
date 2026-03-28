"""
WanClaw Gateway v2 - WebSocket Control Plane

Provides real-time communication, session management, presence tracking,
message routing, and plugin hot-loading.
"""

import asyncio
import json
import time
import logging
import uuid
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class PresenceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    AWAY = "away"


@dataclass
class Session:
    session_id: str
    user_id: str
    channel: str
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Presence:
    user_id: str
    status: PresenceStatus
    last_seen: float
    channels: Set[str] = field(default_factory=set)


class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)

    def subscribe(self, event: str, callback: Callable):
        self._subscribers[event].append(callback)

    def unsubscribe(self, event: str, callback: Callable):
        if callback in self._subscribers[event]:
            self._subscribers[event].remove(callback)

    async def emit(self, event: str, data: Any = None):
        for callback in self._subscribers.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Event handler error for {event}: {e}")


class GatewayV2:
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.presence: Dict[str, Presence] = {}
        self.adapters: Dict[str, Any] = {}
        self.plugins: Dict[str, Any] = {}
        self.event_bus = EventBus()
        self.ws_connections: Dict[str, Any] = {}
        self._cron_tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        self._start_time = time.time()

    async def start(self):
        self._running = True
        logger.info("Gateway v2 starting...")
        await self.event_bus.emit("gateway:start")
        logger.info("Gateway v2 started")

    async def stop(self):
        self._running = False
        for task in self._cron_tasks.values():
            task.cancel()
        for adapter in self.adapters.values():
            if hasattr(adapter, "disconnect"):
                try:
                    await adapter.disconnect()
                except Exception:
                    pass
        await self.event_bus.emit("gateway:stop")
        logger.info("Gateway v2 stopped")

    def register_adapter(self, name: str, adapter: Any):
        self.adapters[name] = adapter
        logger.info(f"Adapter registered: {name}")

    def unregister_adapter(self, name: str):
        if name in self.adapters:
            del self.adapters[name]
            logger.info(f"Adapter unregistered: {name}")

    def get_adapter(self, name: str) -> Optional[Any]:
        return self.adapters.get(name)

    def list_adapters(self) -> List[Dict]:
        result = []
        for name, adapter in self.adapters.items():
            info = {
                "name": name,
                "connected": getattr(adapter, "is_connected", lambda: False)(),
                "stats": getattr(adapter, "get_stats", lambda: {})(),
            }
            result.append(info)
        return result

    def create_session(self, user_id: str, channel: str, metadata: Dict = None) -> Session:
        session_id = str(uuid.uuid4())
        session = Session(session_id=session_id, user_id=user_id, channel=channel, metadata=metadata or {})
        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        session = self.sessions.get(session_id)
        if session:
            session.last_active = time.time()
        return session

    def destroy_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]

    def list_sessions(self, user_id: str = None) -> List[Session]:
        if user_id:
            return [s for s in self.sessions.values() if s.user_id == user_id]
        return list(self.sessions.values())

    def update_presence(self, user_id: str, status: PresenceStatus, channel: str = None):
        if user_id not in self.presence:
            self.presence[user_id] = Presence(user_id=user_id, status=status, last_seen=time.time())
        self.presence[user_id].status = status
        self.presence[user_id].last_seen = time.time()
        if channel:
            self.presence[user_id].channels.add(channel)

    def get_presence(self, user_id: str) -> Optional[Presence]:
        return self.presence.get(user_id)

    async def route_message(self, message: Dict) -> Dict:
        channel = message.get("platform", message.get("channel", ""))
        adapter = self.adapters.get(channel)
        if not adapter:
            return {"success": False, "error": f"No adapter for channel: {channel}"}
        try:
            result = await adapter.handle_message(message)
            await self.event_bus.emit("message:received", {"channel": channel, "message": message, "result": result})
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Message routing error: {e}")
            return {"success": False, "error": str(e)}

    async def send_message(self, channel: str, target: str, content: str, **kwargs) -> Dict:
        adapter = self.adapters.get(channel)
        if not adapter:
            return {"success": False, "error": f"No adapter for channel: {channel}"}
        try:
            result = await adapter.send_message(target, content, **kwargs)
            await self.event_bus.emit("message:sent", {"channel": channel, "target": target, "content": content})
            return {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Send message error: {e}")
            return {"success": False, "error": str(e)}

    async def load_plugin(self, plugin_path: str) -> Dict:
        try:
            import importlib.util
            from pathlib import Path
            p = Path(plugin_path)
            spec = importlib.util.spec_from_file_location("plugin", str(p))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            plugin_name = p.stem
            self.plugins[plugin_name] = module
            if hasattr(module, "register"):
                module.register(self)
            await self.event_bus.emit("plugin:loaded", {"name": plugin_name})
            logger.info(f"Plugin loaded: {plugin_name}")
            return {"success": True, "name": plugin_name}
        except Exception as e:
            logger.error(f"Plugin load failed: {e}")
            return {"success": False, "error": str(e)}

    async def unload_plugin(self, plugin_name: str) -> Dict:
        if plugin_name in self.plugins:
            module = self.plugins[plugin_name]
            if hasattr(module, "unregister"):
                module.unregister(self)
            del self.plugins[plugin_name]
            await self.event_bus.emit("plugin:unloaded", {"name": plugin_name})
            return {"success": True}
        return {"success": False, "error": f"Plugin not found: {plugin_name}"}

    def get_health(self) -> Dict:
        adapter_status = {}
        for name, adapter in self.adapters.items():
            try:
                connected = getattr(adapter, "is_connected", lambda: False)()
            except Exception:
                connected = False
            adapter_status[name] = {"connected": connected}
        return {
            "running": self._running,
            "adapters": adapter_status,
            "sessions": len(self.sessions),
            "plugins": len(self.plugins),
            "uptime": round(time.time() - self._start_time, 1),
        }

    async def handle_ws_connect(self, ws, client_id: str):
        self.ws_connections[client_id] = ws
        self.update_presence(client_id, PresenceStatus.ONLINE)
        await self.event_bus.emit("ws:connect", {"client_id": client_id})
        logger.info(f"WS client connected: {client_id}")

    async def handle_ws_disconnect(self, client_id: str):
        if client_id in self.ws_connections:
            del self.ws_connections[client_id]
        self.update_presence(client_id, PresenceStatus.OFFLINE)
        await self.event_bus.emit("ws:disconnect", {"client_id": client_id})
        logger.info(f"WS client disconnected: {client_id}")

    async def handle_ws_message(self, client_id: str, data: Dict) -> Dict:
        action = data.get("action", "")
        if action == "ping":
            return {"action": "pong", "timestamp": time.time()}
        elif action == "subscribe":
            event = data.get("event", "")
            return {"action": "subscribed", "event": event}
        elif action == "send":
            channel = data.get("channel", "")
            target = data.get("target", "")
            content = data.get("content", "")
            return await self.send_message(channel, target, content)
        elif action == "status":
            return {"action": "status", **self.get_health()}
        return {"action": "error", "message": f"Unknown action: {action}"}

    async def broadcast(self, data: Dict):
        disconnected = []
        for client_id, ws in self.ws_connections.items():
            try:
                await ws.send_json(data)
            except Exception:
                disconnected.append(client_id)
        for client_id in disconnected:
            await self.handle_ws_disconnect(client_id)


_gateway_v2: Optional[GatewayV2] = None


def get_gateway_v2() -> GatewayV2:
    global _gateway_v2
    if _gateway_v2 is None:
        _gateway_v2 = GatewayV2()
    return _gateway_v2
