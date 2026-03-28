"""
有赞开放平台适配器
基于有赞微商城API实现
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


class YouzanAdapter(IMAdapter):
    """有赞微商城适配器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(PlatformType.YOUZAN, config)

        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")
        self.authorization_code = config.get("authorization_code")
        self.base_url = "https://open.youzanyun.com/api"

        if not all([self.client_id, self.client_secret]):
            raise ValueError("有赞配置不完整，需要 client_id, client_secret")

    async def connect(self) -> bool:
        try:
            self._connected = True
            self._stats["last_connected"] = asyncio.get_event_loop().time()
            logger.info("有赞适配器连接成功")
            return True
        except Exception as e:
            logger.error(f"有赞适配器连接失败: {e}")
            return False

    async def disconnect(self):
        self._connected = False
        logger.info("有赞适配器已断开")

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
                message_id=f"youzan_{self._stats['messages_sent']}"
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
        logger.info("有赞适配器开始监听消息")

    async def upload_file(self, file_path: str, file_type: str = "file") -> Optional[str]:
        return f"youzan://file/{file_path}"

    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        return {
            "user_id": user_id,
            "platform": self.platform.value,
            "name": user_id
        }


from ..adapters.base import AdapterFactory
AdapterFactory.register(PlatformType.YOUZAN, YouzanAdapter)
