"""
WanClaw Config System

OpenClaw-compatible JSON5-style configuration with strict validation.
Supports env substitution, live reload, and hot patching.
"""

import os
import json
import logging
import time
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "identity": {"name": "WanClaw", "emoji": "🦞"},
    "agent": {"workspace": "~/.wanclaw/workspace", "model": "deepseek/deepseek-chat"},
    "gateway": {"mode": "local", "port": 8000, "bind": "0.0.0.0", "auth_enabled": True, "cors_origins": []},
    "channels": {},
    "tools": {"allow": ["exec", "read", "write", "edit"], "deny": [], "elevated": {"enabled": False}},
    "sandbox": {"mode": "always", "scope": "session", "max_time": 30, "max_memory_mb": 256},
    "heartbeat": {"enabled": True, "interval": 1800},
    "skills": {"allowBundled": True, "sandbox": True},
    "ai": {
        "enabled": True,
        "engine": "zhipu",
        "deepseek": {"api_key": "", "model": "deepseek-chat"},
        "ollama": {"base_url": "http://localhost:11434", "model": "qwen2.5:7b"},
        "zhipu": {"api_key": "", "model": "glm-4-flash"},
    },
    "security": {
        "auth_required": True,
        "ws_origin_check": True,
        "rate_limit": {"enabled": True, "max_requests": 60, "window_seconds": 60},
        "blocked_commands": ["rm -rf /", "dd if=", "mkfs", ":(){:|:&};:"],
        "max_input_length": 4000,
    },
    "logging": {"level": "info", "file": "logs/wanclaw.log"},
    "memory": {"enabled": True, "base_dir": "~/.wanclaw/memory"},
    "marketplace": {
        "enabled": True,
        "url": "https://wanhub.vanyue.cn",
        "auto_update": True,
        "version_check": True,
    },
}


class WanClawConfig:
    def __init__(self, config_path: str = None):
        self.config_path = Path(config_path or os.path.expanduser("~/.wanclaw/config.json"))
        self.config: Dict[str, Any] = {}
        self._load()

    def _load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    self.config = json.load(f)
                logger.info(f"Config loaded from {self.config_path}")
            except Exception as e:
                logger.warning(f"Config load failed: {e}, using defaults")
                self.config = {}
        self._merge_defaults()

    def _merge_defaults(self):
        for key, value in DEFAULT_CONFIG.items():
            if key not in self.config:
                self.config[key] = value
            elif isinstance(value, dict) and isinstance(self.config[key], dict):
                for sub_key, sub_value in value.items():
                    if sub_key not in self.config[key]:
                        self.config[key][sub_key] = sub_value

    def _substitute_env(self, value: Any) -> Any:
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.environ.get(env_var, value)
        if isinstance(value, dict):
            return {k: self._substitute_env(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._substitute_env(v) for v in value]
        return value

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return self._substitute_env(value)

    def set(self, key: str, value: Any):
        keys = key.split(".")
        target = self.config
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value

    def patch(self, updates: Dict):
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(self.config.get(key), dict):
                self.config[key].update(value)
            else:
                self.config[key] = value

    def save(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        logger.info(f"Config saved to {self.config_path}")

    def validate(self) -> List[str]:
        errors = []
        if self.get("gateway.port", 0) < 1 or self.get("gateway.port", 0) > 65535:
            errors.append("gateway.port must be between 1 and 65535")
        if self.get("ai.enabled") and not self.get(f"ai.{self.get('ai.engine')}.api_key") and self.get("ai.engine") != "ollama":
            errors.append(f"AI engine '{self.get('ai.engine')}' requires an API key")
        if self.get("security.auth_required") and not self.get("gateway.auth_enabled"):
            errors.append("security.auth_required is true but gateway.auth_enabled is false")
        return errors

    def get_all(self) -> Dict:
        return self._substitute_env(self.config)


_config: Optional[WanClawConfig] = None


def get_config(**kwargs) -> WanClawConfig:
    global _config
    if _config is None:
        _config = WanClawConfig(**kwargs)
    return _config
