"""
Channel Adapter — unified interface for WeCom, Feishu, QQ, WeChat, Telegram.

Each platform adapter normalizes messages to {role, content, raw} and
generates session keys at 4 scope levels.
"""
from typing import Any, Dict, Optional
from wanclaw.backend.agent.session_scopes import Scope


CAPABILITY_DEFAULTS = {
    "threading": False,
    "reactions": False,
    "voice": False,
    "groups": False,
    "multi_account": False,
}

PLATFORM_CAPABILITIES: Dict[str, Dict[str, bool]] = {
    "wecom": {
        "threading": False,
        "reactions": False,
        "voice": True,
        "groups": True,
        "multi_account": True,
    },
    "feishu": {
        "threading": True,
        "reactions": True,
        "voice": True,
        "groups": True,
        "multi_account": True,
    },
    "qq": {
        "threading": False,
        "reactions": False,
        "voice": False,
        "groups": True,
        "multi_account": False,
    },
    "wechat": {
        "threading": False,
        "reactions": False,
        "voice": False,
        "groups": False,
        "multi_account": False,
    },
    "telegram": {
        "threading": True,
        "reactions": True,
        "voice": True,
        "groups": True,
        "multi_account": False,
    },
}


class BaseChannelAdapter:
    """Base adapter shared by all platform adapters."""

    platform: str
    config: Dict[str, Any]

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def get_capabilities(self) -> Dict[str, bool]:
        caps = dict(CAPABILITY_DEFAULTS)
        caps.update(PLATFORM_CAPABILITIES.get(self.platform, CAPABILITY_DEFAULTS))
        return caps

    def normalize_message(
        self,
        raw: Dict[str, Any],
        role: str = "user",
    ) -> Dict[str, Any]:
        text = raw.get("text", "")
        result: Dict[str, Any] = {
            "role": role,
            "content": text,
            "raw": dict(raw),
        }
        if "quote" in raw:
            result["quote"] = raw["quote"]
        if "thread_id" in raw:
            result["thread_id"] = raw["thread_id"]
        return result

    def get_session_key(
        self,
        scope: Scope,
        channel: str = "main",
        sub_channel: Optional[str] = None,
        sub_sub_channel: Optional[str] = None,
        sub_sub_sub_channel: Optional[str] = None,
        peer_id: Optional[str] = None,
        account: Optional[str] = None,
        **kwargs: str,
    ) -> str:
        from wanclaw.backend.agent.session_scopes import SessionScopeGenerator

        gen = SessionScopeGenerator()
        return gen.generate_key(
            scope=scope,
            channel=channel,
            sub_channel=sub_channel,
            sub_sub_channel=sub_sub_channel,
            sub_sub_sub_channel=sub_sub_sub_channel,
            peer_id=peer_id,
            account=account,
            **kwargs,
        )

    def send_message(self, content: str, **kwargs: Any) -> None:
        raise NotImplementedError

    def receive(self, **kwargs: Any) -> Dict[str, Any]:
        raise NotImplementedError


class WeComAdapter(BaseChannelAdapter):
    platform = "wecom"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.corp_id = config.get("corp_id", "")
        self.agent_id = config.get("agent_id", "")


class FeishuAdapter(BaseChannelAdapter):
    platform = "feishu"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.app_id = config.get("app_id", "")


class QQAdapter(BaseChannelAdapter):
    platform = "qq"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.uin = config.get("uin", "")


class WeChatAdapter(BaseChannelAdapter):
    platform = "wechat"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.app_id = config.get("app_id", "")


class TelegramAdapter(BaseChannelAdapter):
    platform = "telegram"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.bot_token = config.get("bot_token", "")


_ADAPTERS: Dict[str, type] = {
    "wecom": WeComAdapter,
    "feishu": FeishuAdapter,
    "qq": QQAdapter,
    "wechat": WeChatAdapter,
    "telegram": TelegramAdapter,
}


def get_adapter(platform: str, config: Dict[str, Any]) -> BaseChannelAdapter:
    """Factory function to get a platform adapter."""
    cls = _ADAPTERS.get(platform)
    if cls is None:
        raise ValueError(f"Unknown platform: {platform}")
    return cls(config)
