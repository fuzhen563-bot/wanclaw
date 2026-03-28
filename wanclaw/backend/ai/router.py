import asyncio
import logging
import random
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
RATE_LIMIT_KEYWORDS = {"429", "rate", "limit", "too many requests", "quota"}

DEFAULT_CIRCUIT_BREAKER_THRESHOLD = 3
DEFAULT_CIRCUIT_BREAKER_WINDOW_S = 300
DEFAULT_RECOVERY_CHECK_INTERVAL_S = 60


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = DEFAULT_CIRCUIT_BREAKER_THRESHOLD,
        window_seconds: int = DEFAULT_CIRCUIT_BREAKER_WINDOW_S,
        backoff_base: float = 0.5,
        backoff_max: float = 8.0,
    ):
        self.failure_threshold = failure_threshold
        self.window_seconds = window_seconds
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max

        self.consecutive_failures = 0
        self.last_failure_time: Optional[float] = None
        self.open_since: Optional[float] = None
        self._lock = asyncio.Lock()

    def record_success(self):
        self.consecutive_failures = 0
        self.open_since = None

    def record_failure(self):
        self.consecutive_failures += 1
        self.last_failure_time = time.monotonic()
        if self.consecutive_failures >= self.failure_threshold and self.open_since is None:
            self.open_since = time.monotonic()
            logger.warning(
                f"Circuit breaker OPENED after {self.consecutive_failures} consecutive failures"
            )

    def is_open(self) -> bool:
        if self.open_since is None:
            return False
        return (time.monotonic() - self.open_since) < self.window_seconds

    def should_probe(self) -> bool:
        if self.open_since is None:
            return False
        return (time.monotonic() - self.open_since) >= self.window_seconds

    def calculate_backoff(self, attempt: int) -> float:
        base_delay = min(self.backoff_base * (2 ** attempt), self.backoff_max)
        jitter = random.uniform(0, base_delay * 0.5)
        return base_delay + jitter


class ProviderState:
    def __init__(self, name: str, model: str, priority: int, enabled: bool = True):
        self.name = name
        self.model = model
        self.priority = priority
        self.enabled = enabled
        self.circuit_breaker = CircuitBreaker()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "model": self.model,
            "priority": self.priority,
            "enabled": self.enabled,
            "consecutive_failures": self.circuit_breaker.consecutive_failures,
        }


class ModelRouter:
    def __init__(self, llm_client=None, config: Optional[Dict[str, Any]] = None):
        self._llm = llm_client
        cfg = config or {}

        raw_providers = cfg.get(
            "providers",
            [
                {"name": "deepseek", "model": "deepseek-chat", "priority": 1},
                {"name": "openai", "model": "gpt-4o-mini", "priority": 2},
                {"name": "groq", "model": "llama-3.3-70b-versatile", "priority": 3},
                {"name": "baidu", "model": "ernie-4.0-8k", "priority": 4},
                {"name": "hunyuan", "model": "hunyuan-pro", "priority": 5},
                {"name": "siliconflow", "model": "Pro/deepseek-ai/DeepSeek-V3", "priority": 6},
                {"name": "qwen", "model": "qwen-plus", "priority": 7},
                {"name": "zhipu", "model": "glm-4-flash", "priority": 8},
                {"name": "moonshot", "model": "moonshot-v1-8k", "priority": 9},
                {"name": "volcengine", "model": "doubao-pro-32k", "priority": 10},
                {"name": "baichuan", "model": "Baichuan4", "priority": 11},
                {"name": "mistral", "model": "mistral-small-latest", "priority": 12},
                {"name": "anthropic", "model": "claude-3-5-haiku-20241022", "priority": 13},
                {"name": "gemini", "model": "gemini-2.0-flash", "priority": 14},
                {"name": "ollama", "model": "qwen2.5:7b", "priority": 15},
                {"name": "azure", "model": "", "priority": 99, "enabled": False},
            ],
        )
        self.providers: List[ProviderState] = [
            ProviderState(
                name=p["name"],
                model=p["model"],
                priority=p.get("priority", 99),
                enabled=p.get("enabled", True),
            )
            for p in raw_providers
        ]

        self.max_retries = cfg.get("max_retries", 2)
        self.recovery_check_interval = cfg.get(
            "recovery_check_interval", DEFAULT_RECOVERY_CHECK_INTERVAL_S
        )
        self._active_provider: Optional[str] = None
        self._active_model: Optional[str] = None
        self._recovery_check_task: Optional[asyncio.Task] = None

    def set_llm_client(self, client):
        self._llm = client

    async def chat(
        self, messages, system=None, temperature=None, max_tokens=None
    ) -> Dict[str, Any]:
        if self._llm is None:
            return {
                "text": "",
                "error": "No LLM client configured",
                "provider": None,
                "model": None,
            }

        errors: List[Dict] = []
        sorted_providers = sorted(
            [p for p in self.providers if p.enabled or p.circuit_breaker.should_probe()],
            key=lambda x: x.priority,
        )

        for provider in sorted_providers:
            result = await self._try_provider(
                provider, messages, system, temperature, max_tokens, errors
            )
            if result is not None:
                return result

        return {
            "text": "",
            "error": f"All providers failed after {self.max_retries} retries each",
            "provider": None,
            "model": None,
            "all_errors": errors,
        }

    def switch_model(self, provider_name: str, model_name: str) -> bool:
        for p in self.providers:
            if p.name == provider_name:
                p.model = model_name
                p.enabled = True
                p.circuit_breaker.record_success()
                return True
        self.providers.append(
            ProviderState(name=provider_name, model=model_name, priority=99)
        )
        return True

    def enable_provider(self, provider_name: str, enabled: bool = True) -> bool:
        for p in self.providers:
            if p.name == provider_name:
                p.enabled = enabled
                if enabled:
                    p.circuit_breaker.record_success()
                return True
        return False

    def get_status(self) -> Dict[str, Any]:
        return {
            "active_provider": self._active_provider,
            "active_model": self._active_model,
            "providers": [p.to_dict() for p in self.providers],
            "max_retries": self.max_retries,
        }

    def start_recovery_checker(self):
        if self._recovery_check_task is not None and not self._recovery_check_task.done():
            return
        self._recovery_check_task = asyncio.create_task(self._recovery_loop())

    def stop_recovery_checker(self):
        if self._recovery_check_task:
            self._recovery_check_task.cancel()
            self._recovery_check_task = None

    async def _try_provider(
        self,
        provider: ProviderState,
        messages,
        system,
        temperature,
        max_tokens,
        errors: List[Dict],
    ) -> Optional[Dict[str, Any]]:
        assert self._llm is not None, "LLM client not configured"
        pname = provider.name
        model = provider.model

        for attempt in range(self.max_retries):
            if attempt > 0:
                delay = provider.circuit_breaker.calculate_backoff(attempt - 1)
                logger.debug(
                    f"[{pname}] Retry {attempt}/{self.max_retries} after {delay:.2f}s backoff"
                )
                await asyncio.sleep(delay)

            try:
                original_model = getattr(self._llm, "model", None)
                original_provider = getattr(self._llm, "provider", None)
                self._llm.model = model
                self._llm.provider = pname

                result = await self._llm.chat(
                    messages, system=system, temperature=temperature, max_tokens=max_tokens
                )

                if original_model is not None:
                    self._llm.model = original_model
                if original_provider is not None:
                    self._llm.provider = original_provider

                status_code = result.get("status_code", 0)
                error_msg = result.get("error", "")

                if error_msg and status_code in RETRYABLE_STATUS_CODES:
                    errors.append(
                        {
                            "provider": pname,
                            "model": model,
                            "attempt": attempt + 1,
                            "status_code": status_code,
                            "error": error_msg,
                        }
                    )
                    provider.circuit_breaker.record_failure()
                    continue

                provider.circuit_breaker.record_success()
                self._active_provider = pname
                self._active_model = model
                result["provider"] = pname
                result["model"] = model
                return result

            except Exception as e:
                errors.append(
                    {
                        "provider": pname,
                        "model": model,
                        "attempt": attempt + 1,
                        "error": str(e),
                    }
                )
                provider.circuit_breaker.record_failure()

                exc_lower = str(e).lower()
                if any(kw in exc_lower for kw in RATE_LIMIT_KEYWORDS):
                    continue

                break

        self._maybe_disable_provider(provider)
        return None

    def _maybe_disable_provider(self, provider: ProviderState):
        cb = provider.circuit_breaker
        if cb.consecutive_failures >= cb.failure_threshold:
            provider.enabled = False
            logger.warning(
                f"Provider '{provider.name}' disabled after {cb.consecutive_failures} "
                f"consecutive failures. Will retry in {cb.window_seconds}s."
            )

    async def _recovery_loop(self):
        while True:
            try:
                await asyncio.sleep(self.recovery_check_interval)
                await self._check_recovery()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Recovery check loop error: {e}")

    async def _check_recovery(self):
        disabled = [p for p in self.providers if not p.enabled]
        if not disabled:
            return

        for provider in disabled:
            if not provider.circuit_breaker.should_probe():
                continue

            logger.info(f"Probing disabled provider '{provider.name}' for recovery...")
            try:
                success = await self._probe_provider(provider)
                if success:
                    provider.enabled = True
                    provider.circuit_breaker.record_success()
                    logger.info(f"Provider '{provider.name}' re-enabled after recovery probe.")
            except Exception:
                cb = provider.circuit_breaker
                cb.open_since = time.monotonic()

    async def _probe_provider(self, provider: ProviderState) -> bool:
        assert self._llm is not None, "LLM client not configured"
        if not hasattr(self._llm, "check_health"):
            try:
                result = await self._llm.chat(
                    [{"role": "user", "content": "ping"}],
                    system=None,
                    temperature=0,
                    max_tokens=1,
                )
                return result.get("error") is None
            except Exception:
                return False

        old_provider = getattr(self._llm, "provider", None)
        old_model = getattr(self._llm, "model", None)
        try:
            self._llm.provider = provider.name
            self._llm.model = provider.model
            healthy = await self._llm.check_health()
            return bool(healthy)
        except Exception:
            return False
        finally:
            if old_provider is not None:
                self._llm.provider = old_provider
            if old_model is not None:
                self._llm.model = old_model


_router: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
