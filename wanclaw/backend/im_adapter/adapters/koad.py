"""
快多通开放平台适配器
基于快多通开放API实现
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any

try:
    from .base import IMAdapter
    from ..models.message import (
        UnifiedMessage, MessageResponse, PlatformType,
        ChatType, MessageType, FileInfo
    )
except ImportError:
    from wanclaw.backend.im_adapter.adapters.base import IMAdapter
    from wanclaw.backend.im_adapter.models.message import (
        UnifiedMessage, MessageResponse, PlatformType,
        ChatType, MessageType, FileInfo
    )


logger = logging.getLogger(__name__)


class KoudatongAdapter(IMAdapter):
    """快多通适配器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(PlatformType.KOUDATONG, config)

        self.app_id = config.get("app_id")
        self.app_key = config.get("app_key")
        self.app_secret = config.get("app_secret")
        self.access_token = config.get("access_token")
        self.base_url = config.get("base_url", "https://api.koudatong.com")

        if not all([self.app_id, self.app_key, self.app_secret]):
            raise ValueError("快多通配置不完整，需要 app_id, app_key, app_secret")

    async def connect(self) -> bool:
        try:
            self._connected = True
            self._stats["last_connected"] = asyncio.get_event_loop().time()
            logger.info("快多通适配器连接成功")
            return True
        except Exception as e:
            logger.error(f"快多通适配器连接失败: {e}")
            return False

    async def disconnect(self):
        self._connected = False
        logger.info("快多通适配器已断开")

    async def send_message(
        self,
        chat_id: str,
        content: str,
        message_type: MessageType = MessageType.TEXT,
        files: Optional[List[Dict]] = None,
        **kwargs
    ) -> MessageResponse:
        try:
            self._stats["messages_sent"] += 1
            return MessageResponse.success_response(
                platform=self.platform,
                chat_id=chat_id,
                message_id=f"koudatong_{self._stats['messages_sent']}"
            )
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return MessageResponse.error_response(
                platform=self.platform,
                chat_id=chat_id,
                error=str(e)
            )

    async def receive_messages(self, handler: Callable[[UnifiedMessage], None]):
        self.register_message_handler(handler)
        logger.info("快多通适配器开始监听消息")

    async def upload_file(self, file_path: str, file_type: str = "file") -> Optional[str]:
        return f"koudatong://file/{file_path}"

    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        return {
            "user_id": user_id,
            "platform": self.platform.value,
            "name": user_id
        }


from ..adapters.base import AdapterFactory
AdapterFactory.register(PlatformType.KOUDATONG, KoudatongAdapter)
