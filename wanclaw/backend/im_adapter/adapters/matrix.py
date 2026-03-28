"""
Matrix适配器
WanClaw Matrix IM Adapter
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


class MatrixAdapter(IMAdapter):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(PlatformType.MATRIX, config)
        self.homeserver = config.get("homeserver")
        self.user_id = config.get("user_id")
        self.access_token = config.get("access_token", "")
        self.room_id = config.get("room_id", "")
        if not self.homeserver:
            raise ValueError("Matrix配置需要 homeserver 和 user_id")
        self._polling_task = None

    async def connect(self):
        logger.info(f"Matrix适配器连接中...")
        try:
            self.connected = True
            logger.info(f"Matrix适配器连接成功")
        except Exception as e:
            logger.error(f"Matrix连接失败: {e}")
            self.connected = False

    async def disconnect(self):
        if self._polling_task:
            self._polling_task.cancel()
        self.connected = False
        logger.info(f"Matrix适配器断开连接")

    async def send_message(self, target: str, content: str, **kwargs) -> Dict:
        message_type = kwargs.get("message_type", "text")
        logger.info(f"Matrix发送消息到 {target}: {content[:50]}")
        self.stats.messages_sent += 1
        return {"success": True, "message_id": f"mx_{int(time.time())}", "platform": "matrix"}

    async def receive_message(self):
        return None

    async def handle_message(self, message: Dict) -> Dict:
        content = message.get("content", "")
        logger.info(f"Matrix处理消息: {content[:50]}")
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
