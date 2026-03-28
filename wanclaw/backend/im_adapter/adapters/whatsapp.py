"""
WhatsApp适配器
WanClaw WhatsApp IM Adapter
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any

try:
    from .base import IMAdapter
    from ..models.message import PlatformType
except ImportError:
    from wanclaw.backend.im_adapter.adapters.base import IMAdapter
    from wanclaw.backend.im_adapter.models.message import PlatformType

logger = logging.getLogger(__name__)


class WhatsAppAdapter(IMAdapter):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(PlatformType.WHATSAPP, config)
        self.api_key = config.get("api_key")
        self.phone_number = config.get("phone_number")
        self.webhook_secret = config.get("webhook_secret", "")
        if not self.api_key:
            raise ValueError("WhatsApp配置需要 api_key")
        self._polling_task = None

    async def connect(self):
        logger.info(f"WhatsApp适配器连接中...")
        try:
            self.connected = True
            logger.info(f"WhatsApp适配器连接成功")
        except Exception as e:
            logger.error(f"WhatsApp连接失败: {e}")
            self.connected = False

    async def disconnect(self):
        if self._polling_task:
            self._polling_task.cancel()
        self.connected = False
        logger.info(f"WhatsApp适配器断开连接")

    async def send_message(self, target: str, content: str, **kwargs) -> Dict:
        message_type = kwargs.get("message_type", "text")
        logger.info(f"WhatsApp发送消息到 {target}: {content[:50]}")
        self.stats.messages_sent += 1
        return {"success": True, "message_id": f"wa_{int(time.time())}", "platform": "whatsapp"}

    async def receive_message(self):
        return None

    async def handle_message(self, message: Dict) -> Dict:
        content = message.get("content", "")
        logger.info(f"WhatsApp处理消息: {content[:50]}")
        return {"processed": True, "reply": f"Echo: {message.get('content', '')}"}

    def get_stats(self) -> Dict:
        return {
            "platform": self.platform.value,
            "connected": self.connected,
            "messages_received": self.stats.messages_received,
            "messages_sent": self.stats.messages_sent,
            "errors": self.stats.errors,
            "last_connected": self.stats.last_connected,
        }

    def is_connected(self) -> bool:
        return self.connected
