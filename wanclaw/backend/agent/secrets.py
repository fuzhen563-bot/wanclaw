import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


SECRET_SURFACES = {
    "ai.deepseek.api_key": "deepseek",
    "ai.qwen.api_key": "qwen",
    "ai.zhipu.api_key": "zhipu",
    "ai.moonshot.api_key": "moonshot",
    "ai.ollama.api_key": "ollama",
    "ai.openai.api_key": "openai",
    "ai.google.api_key": "google",
    "ai.anthropic.api_key": "anthropic",
    "ai.vertex.project_id": "vertex",
    "gateway.auth.token": "gateway_auth",
    "gateway.auth.password": "gateway_password",
    "gateway.ws_origin": "gateway_ws",
    "memory.ollama.base_url": "ollama_mem",
    "memory.qdrant.url": "qdrant",
    "memory.qdrant.api_key": "qdrant_key",
    "websearch.brave.key": "brave",
    "websearch.perplexity.key": "perplexity",
    "websearch.serper.key": "serper",
    "voice.tts.key": "tts",
    "voice.stt.key": "stt",
    "channels.telegram.bot_token": "telegram",
    "channels.discord.bot_token": "discord",
    "channels.slack.bot_token": "slack",
    "channels.slack.signing_secret": "slack_signing",
    "channels.whatsapp.phone_number": "whatsapp",
    "channels.whatsapp.jwt_token": "whatsapp_jwt",
    "channels.signal.phone": "signal",
    "channels.signal.username": "signal_user",
    "channels.matrix.homeserver": "matrix",
    "channels.matrix.access_token": "matrix_token",
    "channels.feishu.app_id": "feishu",
    "channels.feishu.app_secret": "feishu_secret",
    "channels.wecom.corp_id": "wecom",
    "channels.wecom.agent_id": "wecom_agent",
    "channels.wecom.secret": "wecom_secret",
    "channels.jd.app_key": "jd",
    "channels.jd.app_secret": "jd_secret",
    "channels.taobao.app_key": "taobao",
    "channels.taobao.app_secret": "taobao_secret",
    "channels.pinduoduo.client_id": "pinduoduo",
    "channels.pinduoduo.client_secret": "pinduoduo_secret",
    "channels.douyin.app_key": "douyin",
    "channels.douyin.app_secret": "douyin_secret",
    "channels.kuaishou.app_id": "kuaishou",
    "channels.kuaishou.app_secret": "kuaishou_secret",
    "channels.youzan.client_id": "youzan",
    "channels.youzan.client_secret": "youzan_secret",
    "plugins.clawhub.token": "clawhub",
    "plugins.registry.npm_token": "npm_registry",
    "docker.registry.username": "docker_user",
    "docker.registry.password": "docker_pass",
    "smtp.host": "smtp",
    "smtp.username": "smtp_user",
    "smtp.password": "smtp_pass",
    "database.url": "database",
    "database.username": "db_user",
    "database.password": "db_pass",
    "redis.url": "redis",
    "redis.password": "redis_pass",
    "s3.bucket": "s3",
    "s3.access_key": "s3_key",
    "s3.secret_key": "s3_secret",
}


class SecretRef:
    def __init__(self, ref: str):
        self.raw = ref
        if ref.startswith("${") and ref.endswith("}"):
            self.kind = "vault"
            self.name = ref[2:-1]
        elif ref.startswith("secret:"):
            self.kind = "vault"
            self.name = ref[8:]
        else:
            self.kind = "env"
            self.name = ref


class SecretsManager:
    def __init__(self, vault_path: str = None):
        if vault_path is None:
            vault_path = os.path.expanduser("~/.wanclaw/secrets.vault")
        self.vault_path = Path(vault_path)
        self._secrets: Dict[str, Dict] = {}
        self._surfaces: Dict[str, str] = dict(SECRET_SURFACES)
        self._fail_fast = True
        self._unresolved: Dict[str, List[str]] = {}
        self._load()

    def _load(self):
        if not self.vault_path.exists():
            return
        try:
            with open(self.vault_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._secrets = data.get("secrets", {})
        except Exception as e:
            logger.error(f"Secrets vault load error: {e}")

    def _save(self):
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.vault_path, "w", encoding="utf-8") as f:
            json.dump({"secrets": self._secrets, "version": "1.1"}, f, ensure_ascii=False, indent=2)
        os.chmod(self.vault_path, 0o600)

    def set(self, name: str, value: str, kind: str = "env", tags: List[str] = None):
        self._secrets[name] = {"name": name, "value": value, "kind": kind, "tags": tags or []}
        self._save()
        logger.info(f"Secret set: {name} ({kind})")

    def get(self, name: str, resolve_refs: bool = True) -> Optional[str]:
        if name not in self._secrets:
            env_val = os.environ.get(name)
            if env_val:
                return env_val
            if name in self._surfaces and self._fail_fast:
                self._unresolved.setdefault(name, [])
                return None
            return None
        val = self._secrets[name].get("value", "")
        if resolve_refs and val.startswith("${") and val.endswith("}"):
            ref_name = val[2:-1]
            return self.get(ref_name, True)
        return val

    def get_surface(self, surface_key: str) -> Optional[str]:
        return self.get(surface_key)

    def resolve_in_config(self, config: Dict, active_surfaces: List[str] = None) -> Dict:
        active = set(active_surfaces) if active_surfaces else set(self._surfaces.keys())
        self._unresolved.clear()
        result = self._resolve_value(config, active, [])
        if self._unresolved and self._fail_fast:
            raise ValueError(f"Unresolved secrets on active surfaces: {list(self._unresolved.keys())}")
        return result

    def _resolve_value(self, obj, active_surfaces: set, path: List[str]):
        if isinstance(obj, str):
            ref = SecretRef(obj)
            if ref.kind == "vault":
                val = self.get(ref.name, resolve_refs=True)
                if val is None:
                    key_path = ".".join(path)
                    if key_path in active_surfaces:
                        self._unresolved.setdefault(key_path, []).append(ref.name)
                    return obj
                return val
            return obj
        elif isinstance(obj, dict):
            return {k: self._resolve_value(v, active_surfaces, path + [k]) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._resolve_value(item, active_surfaces, path + ["i"]) for item in obj]
        return obj

    def get_all_names(self, kind: str = None) -> List[str]:
        if kind is None:
            return list(self._secrets.keys())
        return [k for k, v in self._secrets.items() if v.get("kind") == kind]

    def delete(self, name: str) -> bool:
        if name in self._secrets:
            del self._secrets[name]
            self._save()
            return True
        return False

    def audit(self) -> Dict:
        configured = []
        missing = []
        for surface, category in self._surfaces.items():
            val = self.get(surface)
            if val:
                configured.append({"surface": surface, "category": category})
            else:
                missing.append({"surface": surface, "category": category})
        return {
            "total_surfaces": len(self._surfaces),
            "configured": len(configured),
            "missing": len(missing),
            "configured_surfaces": configured,
            "missing_surfaces": missing,
        }

    def get_stats(self) -> Dict:
        return {
            "total": len(self._secrets),
            "surfaces_defined": len(self._surfaces),
            "vault_path": str(self.vault_path),
            "fail_fast": self._fail_fast,
        }


_secrets_mgr: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    global _secrets_mgr
    if _secrets_mgr is None:
        _secrets_mgr = SecretsManager()
    return _secrets_mgr
