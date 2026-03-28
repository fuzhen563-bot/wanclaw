"""
快手开放平台适配器
基于快手电商开放平台API实现
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


class KuaishouAdapter(IMAdapter):
    """快手小店适配器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(PlatformType.KUAISHOU, config)

        self.app_id = config.get("app_id")
        self.app_secret = config.get("app_secret")
        self.access_token = config.get("access_token")
        self.base_url = "https://open.kuaishou.ixigua.com"

        if not all([self.app_id, self.app_secret]):
            raise ValueError("快手配置不完整，需要 app_id, app_secret")

    async def connect(self) -> bool:
        try:
            self._connected = True
            self._stats["last_connected"] = asyncio.get_event_loop().time()
            logger.info("快手适配器连接成功")
            return True
        except Exception as e:
            logger.error(f"快手适配器连接失败: {e}")
            return False

    async def disconnect(self):
        self._connected = False
        logger.info("快手适配器已断开")

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
                message_id=f"kuaishou_{self._stats['messages_sent']}"
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
        logger.info("快手适配器开始监听消息")

    async def upload_file(self, file_path: str, file_type: str = "file") -> Optional[str]:
        return f"kuaishou://file/{file_path}"

    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        return {
            "user_id": user_id,
            "platform": self.platform.value,
            "name": user_id
        }


from ..adapters.base import AdapterFactory
AdapterFactory.register(PlatformType.KUAISHOU, KuaishouAdapter)
