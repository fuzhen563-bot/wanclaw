"""
WanClaw 分布式平台核心模块
多模型自动容灾路由 - 模型降级、熔断、自恢复
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from .namespace import TenantNamespace
from .state import CentralStateManager, get_central_state

logger = logging.getLogger(__name__)


class ModelProvider(Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    ZHIPU = "zhipu"
    QWEN = "qwen"
    MOONSHOT = "moonshot"
    WANYUE = "wanyue"
    ANTHROPIC = "anthropic"


class ModelStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    RECOVERING = "recovering"


@dataclass
class ModelEndpoint:
    provider: ModelProvider
    name: str
    url: str
    api_key: Optional[str] = None
    status: ModelStatus = ModelStatus.HEALTHY
    latency_ms: float = 0.0
    error_rate: float = 0.0
    last_error: Optional[str] = None
    last_success: Optional[datetime] = None
    consecutive_failures: int = 0
    max_retries: int = 3
    timeout: int = 30


@dataclass
class RoutingResult:
    success: bool
    provider: ModelProvider
    model_name: str
    response: Any = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    fallback_used: bool = False


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 60, recovery_seconds: int = 300):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.recovery_seconds = recovery_seconds
        self._failure_count: Dict[str, int] = {}
        self._last_failure_time: Dict[str, datetime] = {}
        self._state: Dict[str, str] = {}

    def is_open(self, key: str) -> bool:
        state = self._state.get(key, "closed")
        if state == "open":
            if self._last_failure_time.get(key):
                if datetime.now() - self._last_failure_time[key] > timedelta(seconds=self.recovery_seconds):
                    self._state[key] = "half-open"
                    return False
            return True
        return False

    def record_success(self, key: str):
        self._failure_count[key] = 0
        self._state[key] = "closed"

    def record_failure(self, key: str):
        self._failure_count[key] = self._failure_count.get(key, 0) + 1
        self._last_failure_time[key] = datetime.now()
        if self._failure_count[key] >= self.failure_threshold:
            self._state[key] = "open"

    def get_state(self, key: str) -> str:
        return self._state.get(key, "closed")


class ModelFailoverRouter:
    """
    多模型自动容灾路由
    - 按优先级尝试可用模型
    - 熔断器保护（连续失败自动隔离）
    - 延迟感知路由
    - 模型恢复自动重新启用
    """

    def __init__(self, state: CentralStateManager = None):
        self._state = state
        self._models: Dict[str, ModelEndpoint] = {}
        self._primary_model: Optional[str] = None
        self._circuit_breaker = CircuitBreaker()
        self._lock = asyncio.Lock()
        self._health_check_task: Optional[asyncio.Task] = None

    async def initialize(self):
        if self._state is None:
            self._state = await get_central_state()
        self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def register_model(
        self,
        provider: ModelProvider,
        name: str,
        url: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
    ) -> bool:
        async with self._lock:
            key = f"{provider.value}:{name}"
            model = ModelEndpoint(
                provider=provider,
                name=name,
                url=url,
                api_key=api_key,
                timeout=timeout,
            )
            self._models[key] = model
            if self._primary_model is None:
                self._primary_model = key
            logger.info(f"Model registered: {key} at {url}")
            return True

    async def unregister_model(self, provider: ModelProvider, name: str) -> bool:
        key = f"{provider.value}:{name}"
        async with self._lock:
            if key in self._models:
                del self._models[key]
                if self._primary_model == key:
                    self._primary_model = next(iter(self._models.keys())) if self._models else None
                return True
            return False

    async def route(
        self,
        tenant_id: str,
        prompt: str,
        fallback_order: List[str] = None,
    ) -> RoutingResult:
        if fallback_order is None:
            fallback_order = list(self._models.keys())
        last_error = None
        for model_key in fallback_order:
            if self._circuit_breaker.is_open(model_key):
                continue
            model = self._models.get(model_key)
            if not model or model.status == ModelStatus.DOWN:
                continue
            start = time.time()
            try:
                result = await self._call_model(model, prompt, tenant_id)
                latency = (time.time() - start) * 1000
                self._circuit_breaker.record_success(model_key)
                model.latency_ms = latency
                model.error_rate = max(0, model.error_rate - 0.01)
                model.consecutive_failures = 0
                model.last_success = datetime.now()
                return RoutingResult(
                    success=True,
                    provider=model.provider,
                    model_name=model.name,
                    response=result,
                    latency_ms=latency,
                    fallback_used=model_key != fallback_order[0],
                )
            except Exception as e:
                last_error = str(e)
                model.consecutive_failures += 1
                model.last_error = last_error
                self._circuit_breaker.record_failure(model_key)
                if self._circuit_breaker.get_state(model_key) == "open":
                    model.status = ModelStatus.DOWN
                    logger.warning(f"Circuit breaker opened for {model_key}: {last_error}")
                await self._record_model_error(tenant_id, model_key, last_error)
        return RoutingResult(
            success=False,
            provider=ModelProvider.OLLAMA,
            model_name="",
            error=last_error or "All models failed",
            fallback_used=True,
        )

    async def _call_model(self, model: ModelEndpoint, prompt: str, tenant_id: str) -> Any:
        if model.provider == ModelProvider.OLLAMA:
            return await self._call_ollama(model, prompt)
        elif model.provider == ModelProvider.OPENAI:
            return await self._call_openai(model, prompt)
        elif model.provider == ModelProvider.DEEPSEEK:
            return await self._call_deepseek(model, prompt)
        elif model.provider == ModelProvider.ZHIPU:
            return await self._call_zhipu(model, prompt)
        elif model.provider == ModelProvider.QWEN:
            return await self._call_qwen(model, prompt)
        elif model.provider == ModelProvider.MOONSHOT:
            return await self._call_moonshot(model, prompt)
        elif model.provider == ModelProvider.WANYUE:
            return await self._call_wanyue(model, prompt)
        elif model.provider == ModelProvider.ANTHROPIC:
            return await self._call_anthropic(model, prompt)
        raise ValueError(f"Unsupported provider: {model.provider}")

    async def _call_ollama(self, model: ModelEndpoint, prompt: str) -> Dict[str, Any]:
        import httpx
        async with httpx.AsyncClient(timeout=model.timeout) as client:
            resp = await client.post(
                f"{model.url}/api/generate",
                json={"model": model.name, "prompt": prompt},
            )
            resp.raise_for_status()
            return resp.json()

    async def _call_openai(self, model: ModelEndpoint, prompt: str) -> Dict[str, Any]:
        import httpx
        async with httpx.AsyncClient(timeout=model.timeout) as client:
            headers = {"Authorization": f"Bearer {model.api_key}"}
            resp = await client.post(
                f"{model.url}/chat/completions",
                headers=headers,
                json={"model": model.name, "messages": [{"role": "user", "content": prompt}]},
            )
            resp.raise_for_status()
            return resp.json()

    async def _call_deepseek(self, model: ModelEndpoint, prompt: str) -> Dict[str, Any]:
        import httpx
        async with httpx.AsyncClient(timeout=model.timeout) as client:
            headers = {"Authorization": f"Bearer {model.api_key}"}
            resp = await client.post(
                f"{model.url}/chat/completions",
                headers=headers,
                json={"model": model.name, "messages": [{"role": "user", "content": prompt}]},
            )
            resp.raise_for_status()
            return resp.json()

    async def _call_zhipu(self, model: ModelEndpoint, prompt: str) -> Dict[str, Any]:
        import httpx
        async with httpx.AsyncClient(timeout=model.timeout) as client:
            headers = {"Authorization": f"Bearer {model.api_key}"}
            resp = await client.post(
                f"{model.url}/chat/completions",
                headers=headers,
                json={"model": model.name, "messages": [{"role": "user", "content": prompt}]},
            )
            resp.raise_for_status()
            return resp.json()

    async def _call_qwen(self, model: ModelEndpoint, prompt: str) -> Dict[str, Any]:
        import httpx
        async with httpx.AsyncClient(timeout=model.timeout) as client:
            headers = {"Authorization": f"Bearer {model.api_key}"}
            resp = await client.post(
                f"{model.url}/chat/completions",
                headers=headers,
                json={"model": model.name, "messages": [{"role": "user", "content": prompt}]},
            )
            resp.raise_for_status()
            return resp.json()

    async def _call_moonshot(self, model: ModelEndpoint, prompt: str) -> Dict[str, Any]:
        import httpx
        async with httpx.AsyncClient(timeout=model.timeout) as client:
            headers = {"Authorization": f"Bearer {model.api_key}"}
            resp = await client.post(
                f"{model.url}/chat/completions",
                headers=headers,
                json={"model": model.name, "messages": [{"role": "user", "content": prompt}]},
            )
            resp.raise_for_status()
            return resp.json()

    async def _call_wanyue(self, model: ModelEndpoint, prompt: str) -> Dict[str, Any]:
        import httpx
        async with httpx.AsyncClient(timeout=model.timeout) as client:
            headers = {"Authorization": f"Bearer {model.api_key}"}
            resp = await client.post(
                f"{model.url}/chat/completions",
                headers=headers,
                json={"model": model.name, "messages": [{"role": "user", "content": prompt}]},
            )
            resp.raise_for_status()
            return resp.json()

    async def _call_anthropic(self, model: ModelEndpoint, prompt: str) -> Dict[str, Any]:
        import httpx
        async with httpx.AsyncClient(timeout=model.timeout) as client:
            headers = {"Authorization": f"Bearer {model.api_key}", "x-api-key": model.api_key, "anthropic-version": "2023-06-01"}
            resp = await client.post(
                f"{model.url}/messages",
                headers=headers,
                json={"model": model.name, "messages": [{"role": "user", "content": prompt}]},
            )
            resp.raise_for_status()
            return resp.json()

    async def _record_model_error(self, tenant_id: str, model_key: str, error: str):
        ns = TenantNamespace(tenant_id)
        error_key = ns.stats_key(f"model_error:{model_key}")
        import json
        error_data = {"error": error, "timestamp": datetime.now().isoformat()}
        await self._state._redis.lpush(error_key, json.dumps(error_data, default=str))
        await self._state._redis.expire(error_key, 86400)

    async def _health_check_loop(self):
        while True:
            try:
                await asyncio.sleep(60)
                for key, model in list(self._models.items()):
                    if model.status == ModelStatus.DOWN:
                        if self._circuit_breaker.get_state(key) == "closed":
                            model.status = ModelStatus.RECOVERING
                            logger.info(f"Model {key} entering recovery mode")
            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def get_model_status(self, tenant_id: str) -> List[Dict[str, Any]]:
        result = []
        for key, model in self._models.items():
            result.append({
                "key": key,
                "provider": model.provider.value,
                "name": model.name,
                "status": model.status.value,
                "latency_ms": round(model.latency_ms, 2),
                "error_rate": round(model.error_rate * 100, 2),
                "consecutive_failures": model.consecutive_failures,
                "circuit_breaker_state": self._circuit_breaker.get_state(key),
                "last_error": model.last_error,
            })
        return result

    async def shutdown(self):
        if self._health_check_task:
            self._health_check_task.cancel()


_failover_router: Optional[ModelFailoverRouter] = None


async def get_failover_router() -> ModelFailoverRouter:
    global _failover_router
    if _failover_router is None:
        _failover_router = ModelFailoverRouter()
        await _failover_router.initialize()
    return _failover_router
