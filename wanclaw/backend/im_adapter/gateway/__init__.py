"""
统一IM网关
管理所有平台适配器，提供统一的消息收发接口
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime

try:
    from ..models.message import (
        UnifiedMessage, MessageResponse, PlatformType, ChatType, MessageType
    )
    from ..adapters.base import IMAdapter, AdapterFactory
except ImportError:
    from wanclaw.backend.im_adapter.models.message import (
        UnifiedMessage, MessageResponse, PlatformType, ChatType, MessageType
    )
    from wanclaw.backend.im_adapter.adapters.base import IMAdapter, AdapterFactory


logger = logging.getLogger(__name__)


class IMGateway:
    """
    统一IM网关
    管理所有平台适配器，提供统一接口
    """
    
    def __init__(self):
        self.adapters: Dict[PlatformType, IMAdapter] = {}
        self._running = False
        self._tasks = []
        self._stats = {
            "total_messages_received": 0,
            "total_messages_sent": 0,
            "total_errors": 0,
            "start_time": None
        }
    
    async def start(self):
        """启动网关"""
        if self._running:
            logger.warning("网关已经在运行")
            return
        
        logger.info("启动IM网关...")
        self._running = True
        self._stats["start_time"] = datetime.now()
        
        # 启动所有适配器
        for platform, adapter in self.adapters.items():
            try:
                if await adapter.connect():
                    logger.info(f"平台 {platform} 连接成功")
                else:
                    logger.error(f"平台 {platform} 连接失败")
            except Exception as e:
                logger.error(f"平台 {platform} 连接异常: {e}")
    
    async def stop(self):
        """停止网关"""
        logger.info("停止IM网关...")
        self._running = False
        
        # 停止所有任务
        for task in self._tasks:
            task.cancel()
        
        # 等待任务完成
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        # 断开所有适配器
        for platform, adapter in self.adapters.items():
            try:
                await adapter.disconnect()
                logger.info(f"平台 {platform} 已断开")
            except Exception as e:
                logger.error(f"平台 {platform} 断开异常: {e}")
        
        self._tasks.clear()
        logger.info("IM网关已停止")
    
    def register_adapter(self, platform: PlatformType, adapter: IMAdapter):
        """
        注册适配器
        
        Args:
            platform: 平台类型
            adapter: 适配器实例
        """
        if platform in self.adapters:
            logger.warning(f"平台 {platform} 已注册，将被替换")
        
        self.adapters[platform] = adapter
        logger.info(f"注册平台适配器: {platform}")
    
    def create_and_register(self, platform: PlatformType, config: Dict[str, Any]) -> IMAdapter:
        """
        创建并注册适配器
        
        Args:
            platform: 平台类型
            config: 配置信息
            
        Returns:
            IMAdapter: 创建的适配器实例
        """
        adapter = AdapterFactory.create(platform, config)
        self.register_adapter(platform, adapter)
        return adapter
    
    async def send_message(
        self,
        platform: PlatformType,
        chat_id: str,
        content: str,
        message_type: MessageType = MessageType.TEXT,
        files: Optional[List[Dict]] = None,
        **kwargs
    ) -> MessageResponse:
        """
        发送消息到指定平台
        
        Args:
            platform: 平台类型
            chat_id: 会话ID
            content: 消息内容
            message_type: 消息类型
            files: 文件列表
            **kwargs: 其他参数
            
        Returns:
            MessageResponse: 发送响应
        """
        if platform not in self.adapters:
            return MessageResponse.error_response(
                platform=platform,
                chat_id=chat_id,
                error=f"平台 {platform} 未注册"
            )
        
        try:
            adapter = self.adapters[platform]
            response = await adapter.send_message(
                chat_id=chat_id,
                content=content,
                message_type=message_type,
                files=files,
                **kwargs
            )
            
            if response.success:
                self._stats["total_messages_sent"] += 1
                logger.info(f"消息发送成功: {platform}/{chat_id}")
            else:
                self._stats["total_errors"] += 1
                logger.error(f"消息发送失败: {platform}/{chat_id} - {response.error}")
            
            return response
            
        except Exception as e:
            self._stats["total_errors"] += 1
            logger.error(f"消息发送异常: {platform}/{chat_id} - {e}")
            return MessageResponse.error_response(
                platform=platform,
                chat_id=chat_id,
                error=str(e)
            )
    
    async def broadcast_message(
        self,
        platforms: List[PlatformType],
        chat_ids: List[str],
        content: str,
        message_type: MessageType = MessageType.TEXT,
        files: Optional[List[Dict]] = None,
        **kwargs
    ) -> List[MessageResponse]:
        """
        广播消息到多个平台
        
        Args:
            platforms: 平台列表
            chat_ids: 会话ID列表
            content: 消息内容
            message_type: 消息类型
            files: 文件列表
            **kwargs: 其他参数
            
        Returns:
            List[MessageResponse]: 所有发送响应
        """
        tasks = []
        task_metadata = []  # 保存每个任务对应的平台和chat_id
        
        for platform in platforms:
            if platform not in self.adapters:
                logger.warning(f"平台 {platform} 未注册，跳过广播")
                continue
            
            for chat_id in chat_ids:
                task = self.send_message(
                    platform=platform,
                    chat_id=chat_id,
                    content=content,
                    message_type=message_type,
                    files=files,
                    **kwargs
                )
                tasks.append(task)
                task_metadata.append((platform, chat_id))
        
        if not tasks:
            logger.warning("没有有效的发送任务")
            return []
        
        logger.info(f"开始广播消息到 {len(tasks)} 个目标")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        responses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # 从任务元数据获取平台和chat_id
                if i < len(task_metadata):
                    platform, chat_id = task_metadata[i]
                else:
                    platform = PlatformType.WECOM
                    chat_id = "unknown"
                
                responses.append(MessageResponse.error_response(
                    platform=platform,
                    chat_id=chat_id,
                    error=str(result)
                ))
            else:
                responses.append(result)
        
        return responses
    
    def register_message_handler(self, handler: Callable[[UnifiedMessage], None]):
        """
        注册全局消息处理器
        
        Args:
            handler: 消息处理器函数
        """
        for platform, adapter in self.adapters.items():
            adapter.register_message_handler(handler)
        logger.info(f"注册全局消息处理器")
    
    def register_error_handler(self, handler: Callable[[Exception], None]):
        """
        注册全局错误处理器
        
        Args:
            handler: 错误处理器函数
        """
        for platform, adapter in self.adapters.items():
            adapter.register_error_handler(handler)
        logger.info(f"注册全局错误处理器")
    
    def get_adapter(self, platform: PlatformType) -> Optional[IMAdapter]:
        """获取指定平台的适配器"""
        return self.adapters.get(platform)
    
    def get_all_adapters(self) -> Dict[PlatformType, IMAdapter]:
        """获取所有适配器"""
        return self.adapters.copy()
    
    async def health_check(self) -> Dict[str, Any]:
        """
        网关健康检查
        
        Returns:
            Dict: 健康状态信息
        """
        adapter_health = {}
        for platform, adapter in self.adapters.items():
            try:
                health = await adapter.health_check()
                adapter_health[platform.value] = health
            except Exception as e:
                adapter_health[platform.value] = {
                    "error": str(e),
                    "connected": False
                }
        
        return {
            "running": self._running,
            "adapter_count": len(self.adapters),
            "stats": self._stats,
            "uptime": (datetime.now() - self._stats["start_time"]).total_seconds() if self._stats["start_time"] else 0,
            "adapters": adapter_health,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取网关统计信息"""
        stats = self._stats.copy()
        stats["running"] = self._running
        stats["adapter_count"] = len(self.adapters)
        stats["connected_adapters"] = sum(1 for a in self.adapters.values() if a.is_connected)
        return stats
    
    @property
    def is_running(self) -> bool:
        """网关是否在运行"""
        return self._running
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.stop()


# 全局网关实例
_gateway: Optional[IMGateway] = None


def get_gateway() -> IMGateway:
    """获取全局网关实例"""
    global _gateway
    if _gateway is None:
        _gateway = IMGateway()
    return _gateway