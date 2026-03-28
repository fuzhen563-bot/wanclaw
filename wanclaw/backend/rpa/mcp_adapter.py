"""
WanClaw MCP Adapter - Model Context Protocol 适配层
原生支持MCP协议，无缝对接第三方RPA工具、系统API、SaaS平台
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class MCPConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    ERROR = "error"


@dataclass
class MCPEndpoint:
    endpoint_id: str
    name: str
    url: str
    protocol: str = "http"
    auth_type: str = "none"
    auth_config: Dict[str, Any] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    status: MCPConnectionState = MCPConnectionState.DISCONNECTED
    last_connected: Optional[datetime] = None


@dataclass
class MCPRequest:
    request_id: str
    endpoint_id: str
    method: str
    params: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MCPResponse:
    request_id: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0


class MCPTool:
    def __init__(self, name: str, description: str, input_schema: Dict, output_schema: Dict = None):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema or {}

    def to_mcp_format(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


class MCPAdapter:
    def __init__(self, tenant_id: str = "default"):
        self.tenant_id = tenant_id
        self._endpoints: Dict[str, MCPEndpoint] = {}
        self._tools: Dict[str, Dict[str, MCPTool]] = {}
        self._request_handlers: Dict[str, Callable] = {}
        self._builtin_tools: Dict[str, MCPTool] = {}
        self._register_builtin_tools()

    def _register_builtin_tools(self):
        self._builtin_tools["http_request"] = MCPTool(
            name="http_request",
            description="发送HTTP请求到指定URL",
            input_schema={
                "type": "object",
                "properties": {
                    "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]},
                    "url": {"type": "string"},
                    "headers": {"type": "object"},
                    "body": {"type": "object"},
                },
                "required": ["method", "url"],
            },
        )
        self._builtin_tools["api_call"] = MCPTool(
            name="api_call",
            description="调用REST API",
            input_schema={
                "type": "object",
                "properties": {
                    "endpoint": {"type": "string"},
                    "action": {"type": "string"},
                    "params": {"type": "object"},
                },
                "required": ["endpoint", "action"],
            },
        )
        self._builtin_tools["webhook_trigger"] = MCPTool(
            name="webhook_trigger",
            description="触发Webhook",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "event": {"type": "string"},
                    "payload": {"type": "object"},
                },
                "required": ["url"],
            },
        )

    async def register_endpoint(
        self,
        name: str,
        url: str,
        protocol: str = "http",
        auth_type: str = "none",
        auth_config: Dict[str, Any] = None,
        capabilities: List[str] = None,
    ) -> str:
        endpoint_id = f"ep-{uuid.uuid4().hex[:8]}"
        endpoint = MCPEndpoint(
            endpoint_id=endpoint_id,
            name=name,
            url=url,
            protocol=protocol,
            auth_type=auth_type,
            auth_config=auth_config or {},
            capabilities=capabilities or [],
        )
        self._endpoints[endpoint_id] = endpoint
        self._tools[endpoint_id] = {}
        logger.info(f"Registered MCP endpoint: {name} ({endpoint_id})")
        return endpoint_id

    async def unregister_endpoint(self, endpoint_id: str) -> bool:
        if endpoint_id in self._endpoints:
            del self._endpoints[endpoint_id]
            if endpoint_id in self._tools:
                del self._tools[endpoint_id]
            logger.info(f"Unregistered MCP endpoint: {endpoint_id}")
            return True
        return False

    async def connect(self, endpoint_id: str) -> bool:
        endpoint = self._endpoints.get(endpoint_id)
        if not endpoint:
            return False
        try:
            endpoint.status = MCPConnectionState.CONNECTING
            if endpoint.protocol == "http":
                import httpx
                async with httpx.AsyncClient() as client:
                    if endpoint.auth_type == "bearer":
                        headers = {"Authorization": f"Bearer {endpoint.auth_config.get('token', '')}"}
                    else:
                        headers = {}
                    resp = await client.get(endpoint.url, headers=headers, timeout=5)
                    if resp.status_code < 400:
                        endpoint.status = MCPConnectionState.CONNECTED
                        endpoint.last_connected = datetime.now()
                        return True
            endpoint.status = MCPConnectionState.ERROR
            return False
        except Exception as e:
            logger.error(f"MCP connect failed: {e}")
            endpoint.status = MCPConnectionState.ERROR
            return False

    async def disconnect(self, endpoint_id: str) -> bool:
        endpoint = self._endpoints.get(endpoint_id)
        if endpoint:
            endpoint.status = MCPConnectionState.DISCONNECTED
            return True
        return False

    async def register_tool(self, endpoint_id: str, tool: MCPTool) -> bool:
        if endpoint_id not in self._endpoints:
            return False
        self._tools[endpoint_id][tool.name] = tool
        logger.info(f"Registered tool {tool.name} for endpoint {endpoint_id}")
        return True

    async def call_tool(
        self,
        endpoint_id: str,
        tool_name: str,
        params: Dict[str, Any],
    ) -> MCPResponse:
        request_id = f"req-{uuid.uuid4().hex[:12]}"
        start_time = asyncio.get_event_loop().time()

        if tool_name in self._builtin_tools:
            return await self._call_builtin_tool(request_id, tool_name, params, start_time)

        endpoint = self._endpoints.get(endpoint_id)
        if not endpoint:
            return MCPResponse(request_id=request_id, success=False, error="Endpoint not found", duration_ms=0)

        tool = self._tools.get(endpoint_id, {}).get(tool_name)
        if not tool:
            return MCPResponse(request_id=request_id, success=False, error=f"Tool {tool_name} not found", duration_ms=0)

        try:
            import httpx
            headers = {"Content-Type": "application/json"}
            if endpoint.auth_type == "bearer":
                headers["Authorization"] = f"Bearer {endpoint.auth_config.get('token', '')}"
            elif endpoint.auth_type == "api_key":
                headers["X-API-Key"] = endpoint.auth_config.get("api_key", "")

            payload = {"method": tool_name, "params": params, "jsonrpc": "2.0", "id": request_id}
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{endpoint.url}/tools/{tool_name}",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                return MCPResponse(
                    request_id=request_id,
                    success=True,
                    data=data,
                    duration_ms=duration_ms,
                )
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            return MCPResponse(request_id=request_id, success=False, error=str(e), duration_ms=duration_ms)

    async def _call_builtin_tool(
        self,
        request_id: str,
        tool_name: str,
        params: Dict[str, Any],
        start_time: float,
    ) -> MCPResponse:
        try:
            if tool_name == "http_request":
                import httpx
                method = params.get("method", "GET")
                url = params.get("url", "")
                headers = params.get("headers", {})
                body = params.get("body")
                async with httpx.AsyncClient(timeout=30) as client:
                    if method == "GET":
                        resp = await client.get(url, headers=headers)
                    elif method == "POST":
                        resp = await client.post(url, headers=headers, json=body)
                    elif method == "PUT":
                        resp = await client.put(url, headers=headers, json=body)
                    elif method == "DELETE":
                        resp = await client.delete(url, headers=headers)
                    else:
                        return MCPResponse(request_id=request_id, success=False, error=f"Unsupported method: {method}")
                    duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                    return MCPResponse(
                        request_id=request_id,
                        success=True,
                        data={"status": resp.status_code, "body": resp.text[:1000]},
                        duration_ms=duration_ms,
                    )
            elif tool_name == "webhook_trigger":
                import httpx
                url = params.get("url", "")
                event = params.get("event", "trigger")
                payload = params.get("payload", {})
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(url, json={"event": event, "data": payload})
                    duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                    return MCPResponse(
                        request_id=request_id,
                        success=resp.status_code < 400,
                        data={"status": resp.status_code},
                        duration_ms=duration_ms,
                    )
            return MCPResponse(request_id=request_id, success=False, error=f"Unknown builtin tool: {tool_name}")
        except Exception as e:
            duration_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            return MCPResponse(request_id=request_id, success=False, error=str(e), duration_ms=duration_ms)

    async def discover_tools(self, endpoint_id: str) -> List[Dict]:
        endpoint = self._endpoints.get(endpoint_id)
        if not endpoint:
            return []
        tools = list(self._builtin_tools.values())
        endpoint_tools = self._tools.get(endpoint_id, {}).values()
        tools.extend(endpoint_tools)
        return [t.to_mcp_format() for t in tools]

    def get_endpoints(self) -> List[MCPEndpoint]:
        return list(self._endpoints.values())

    def get_endpoint(self, endpoint_id: str) -> Optional[MCPEndpoint]:
        return self._endpoints.get(endpoint_id)

    def list_all_tools(self) -> Dict[str, List[Dict]]:
        result = {ep_id: [t.to_mcp_format() for t in tools.values()] for ep_id, tools in self._tools.items()}
        result["builtin"] = [t.to_mcp_format() for t in self._builtin_tools.values()]
        return result


_mcp_instances: Dict[str, MCPAdapter] = {}


def get_mcp_adapter(tenant_id: str = "default") -> MCPAdapter:
    if tenant_id not in _mcp_instances:
        _mcp_instances[tenant_id] = MCPAdapter(tenant_id)
    return _mcp_instances[tenant_id]
