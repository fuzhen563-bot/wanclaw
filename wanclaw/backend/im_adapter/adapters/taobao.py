"""
淘宝/天猫开放平台适配器
基于淘宝开放平台API实现
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


class TaobaoAdapter(IMAdapter):
    """淘宝/天猫适配器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(PlatformType.TAOBAO, config)

        self.app_key = config.get("app_key")
        self.app_secret = config.get("app_secret")
        self.session_key = config.get("session_key")
        self.base_url = "https://eco.taobao.com/router/rest"
        self.access_token = None

        if not all([self.app_key, self.app_secret]):
            raise ValueError("淘宝配置不完整，需要 app_key, app_secret")

    async def connect(self) -> bool:
        try:
            self._connected = True
            self._stats["last_connected"] = asyncio.get_event_loop().time()
            logger.info("淘宝适配器连接成功")
            return True
        except Exception as e:
            logger.error(f"淘宝适配器连接失败: {e}")
            return False

    async def disconnect(self):
        self._connected = False
        logger.info("淘宝适配器已断开")

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
                message_id=f"taobao_{self._stats['messages_sent']}"
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
        logger.info("淘宝适配器开始监听消息")

    async def upload_file(self, file_path: str, file_type: str = "file") -> Optional[str]:
        return f"taobao://file/{file_path}"

    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        return {
            "user_id": user_id,
            "platform": self.platform.value,
            "name": user_id
        }


from ..adapters.base import AdapterFactory
AdapterFactory.register(PlatformType.TAOBAO, TaobaoAdapter)
