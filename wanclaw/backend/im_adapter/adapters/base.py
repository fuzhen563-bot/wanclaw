"""
IM适配器基类定义
提供统一的适配器接口
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime

try:
    from ..models.message import (
        UnifiedMessage, MessageResponse, PlatformType, ChatType, MessageType
    )
except ImportError:
    from wanclaw.backend.im_adapter.models.message import (
        UnifiedMessage, MessageResponse, PlatformType, ChatType, MessageType
    )


logger = logging.getLogger(__name__)


class IMAdapter(ABC):
    """IM适配器基类"""
    
    def __init__(self, platform: PlatformType, config: Dict[str, Any]):
        """
        初始化适配器
        
        Args:
            platform: 平台类型
            config: 配置信息
        """
        self.platform = platform
        self.config = config
        self._connected = False
        self._message_handlers = []
        self._error_handlers = []
        self._stats = {
            "messages_received": 0,
            "messages_sent": 0,
            "errors": 0,
            "last_connected": None
        }
    
    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._connected
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        连接到平台
        
        Returns:
            bool: 连接是否成功
        """
        pass
    
    @abstractmethod
    async def disconnect(self):
        """断开连接"""
        pass
    
    @abstractmethod
    async def send_message(
        self,
        chat_id: str,
        content: str,
        message_type: MessageType = MessageType.TEXT,
        files: Optional[List[Dict]] = None,
        **kwargs
    ) -> MessageResponse:
        """
        发送消息
        
        Args:
            chat_id: 会话ID
            content: 消息内容
            message_type: 消息类型
            files: 文件列表
            **kwargs: 其他参数
            
        Returns:
            MessageResponse: 发送响应
        """
        pass
    
    @abstractmethod
    async def receive_messages(self, handler: Callable[[UnifiedMessage], None]):
        """
        接收消息
        
        Args:
            handler: 消息处理器回调函数
        """
        pass
    
    @abstractmethod
    async def upload_file(self, file_path: str, file_type: str = "file") -> Optional[str]:
        """
        上传文件到平台
        
        Args:
            file_path: 文件路径
            file_type: 文件类型
            
        Returns:
            str: 文件URL或文件ID
        """
        pass
    
    @abstractmethod
    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 用户信息
        """
        pass
    
    def register_message_handler(self, handler: Callable[[UnifiedMessage], None]):
        """注册消息处理器"""
        self._message_handlers.append(handler)
        logger.info(f"注册消息处理器到平台 {self.platform}")
    
    def register_error_handler(self, handler: Callable[[Exception], None]):
        """注册错误处理器"""
        self._error_handlers.append(handler)
    
    async def _handle_message(self, message: UnifiedMessage):
        """处理接收到的消息"""
        try:
            self._stats["messages_received"] += 1
            logger.debug(f"平台 {self.platform} 收到消息: {message.message_id}")
            
            # 调用所有注册的处理器
            for handler in self._message_handlers:
                try:
                    await handler(message)
                except Exception as e:
                    logger.error(f"消息处理器错误: {e}")
                    await self._handle_error(e)
        except Exception as e:
            logger.error(f"消息处理错误: {e}")
            await self._handle_error(e)
    
    async def _handle_error(self, error: Exception):
        """处理错误"""
        self._stats["errors"] += 1
        logger.error(f"平台 {self.platform} 错误: {error}")
        
        # 调用所有注册的错误处理器
        for handler in self._error_handlers:
            try:
                await handler(error)
            except Exception as e:
                logger.error(f"错误处理器错误: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self._stats.copy()
        stats["connected"] = self._connected
        stats["platform"] = self.platform.value
        stats["handler_count"] = len(self._message_handlers)
        return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            Dict: 健康状态信息
        """
        return {
            "platform": self.platform.value,
            "connected": self._connected,
            "stats": self.get_stats(),
            "timestamp": datetime.now().isoformat()
        }
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.disconnect()


class AdapterFactory:
    """适配器工厂类"""
    
    _adapters = {}
    
    @classmethod
    def register(cls, platform: PlatformType, adapter_class):
        """注册适配器类"""
        cls._adapters[platform] = adapter_class
        logger.info(f"注册适配器: {platform} -> {adapter_class.__name__}")
    
    @classmethod
    def create(cls, platform: PlatformType, config: Dict[str, Any]) -> IMAdapter:
        """
        创建适配器实例
        
        Args:
            platform: 平台类型
            config: 配置信息
            
        Returns:
            IMAdapter: 适配器实例
            
        Raises:
            ValueError: 平台不支持
        """
        if platform not in cls._adapters:
            raise ValueError(f"平台 {platform} 不支持")
        
        adapter_class = cls._adapters[platform]
        return adapter_class(config)
    
    @classmethod
    def get_supported_platforms(cls) -> List[PlatformType]:
        """获取支持的平台列表"""
        return list(cls._adapters.keys())