"""
Telegram适配器
基于python-telegram-bot库实现
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime

from telegram import Bot, Update, Message as TGMessage
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.constants import ParseMode

try:
    from .base import IMAdapter
    from ..models.message import (
        UnifiedMessage, MessageResponse, PlatformType, 
        ChatType, MessageType, FileInfo, MentionInfo
    )
except ImportError:
    from wanclaw.backend.im_adapter.adapters.base import IMAdapter
    from wanclaw.backend.im_adapter.models.message import (
        UnifiedMessage, MessageResponse, PlatformType, 
        ChatType, MessageType, FileInfo, MentionInfo
    )


logger = logging.getLogger(__name__)


class TelegramAdapter(IMAdapter):
    """Telegram适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(PlatformType.TELEGRAM, config)
        
        # Telegram配置
        self.bot_token = config.get("bot_token")
        self.proxy_url = config.get("proxy_url")
        
        # Bot实例
        self.bot: Optional[Bot] = None
        self.application: Optional[Application] = None
        
        # 轮询任务
        self.polling_task = None
        
        if not self.bot_token:
            raise ValueError("Telegram配置需要 bot_token")
    
    async def connect(self) -> bool:
        """连接到Telegram"""
        try:
            # 创建Bot实例
            bot_kwargs = {}
            if self.proxy_url:
                bot_kwargs["proxy"] = self.proxy_url
            
            self.bot = Bot(token=self.bot_token, **bot_kwargs)
            
            # 创建Application
            self.application = Application.builder().token(self.bot_token).build()
            
            # 测试连接
            bot_info = await self.bot.get_me()
            logger.info(f"Telegram Bot连接成功: @{bot_info.username} ({bot_info.id})")
            
            self._connected = True
            self._stats["last_connected"] = asyncio.get_event_loop().time()
            return True
            
        except Exception as e:
            logger.error(f"Telegram适配器连接失败: {e}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        if self.application:
            await self.application.shutdown()
        
        if self.bot:
            await self.bot.close()
        
        if self.polling_task:
            self.polling_task.cancel()
            try:
                await self.polling_task
            except asyncio.CancelledError:
                pass
        
        self._connected = False
        logger.info("Telegram适配器已断开")
    
    async def send_message(
        self,
        chat_id: str,
        content: str,
        message_type: MessageType = MessageType.TEXT,
        files: Optional[List[Dict]] = None,
        **kwargs
    ) -> MessageResponse:
        """
        发送消息到Telegram
        
        Telegram支持的消息类型:
        - text: 文本消息
        - image: 图片消息
        - voice: 语音消息
        - video: 视频消息
        - file: 文件消息
        - sticker: 贴纸
        """
        try:
            if not self.bot:
                return MessageResponse.error_response(
                    platform=self.platform,
                    chat_id=chat_id,
                    error="Bot未初始化"
                )
            
            parse_mode = kwargs.get("parse_mode", ParseMode.MARKDOWN)
            disable_notification = kwargs.get("disable_notification", False)
            disable_web_page_preview = kwargs.get("disable_web_page_preview", False)
            
            # 根据消息类型发送
            if message_type == MessageType.TEXT:
                message = await self.bot.send_message(
                    chat_id=chat_id,
                    text=content,
                    parse_mode=parse_mode,
                    disable_notification=disable_notification,
                    disable_web_page_preview=disable_web_page_preview
                )
                
            elif message_type == MessageType.IMAGE:
                # 发送图片
                if files and files[0].get("path"):
                    # 从本地文件发送
                    with open(files[0]["path"], "rb") as photo:
                        message = await self.bot.send_photo(
                            chat_id=chat_id,
                            photo=photo,
                            caption=content,
                            parse_mode=parse_mode,
                            disable_notification=disable_notification
                        )
                elif files and files[0].get("url"):
                    # 从URL发送
                    message = await self.bot.send_photo(
                        chat_id=chat_id,
                        photo=files[0]["url"],
                        caption=content,
                        parse_mode=parse_mode,
                        disable_notification=disable_notification
                    )
                else:
                    # 没有文件，发送文本
                    message = await self.bot.send_message(
                        chat_id=chat_id,
                        text=content,
                        parse_mode=parse_mode
                    )
                    
            elif message_type == MessageType.FILE:
                # 发送文件
                if files and files[0].get("path"):
                    with open(files[0]["path"], "rb") as document:
                        message = await self.bot.send_document(
                            chat_id=chat_id,
                            document=document,
                            caption=content,
                            parse_mode=parse_mode,
                            disable_notification=disable_notification
                        )
                elif files and files[0].get("url"):
                    message = await self.bot.send_document(
                        chat_id=chat_id,
                        document=files[0]["url"],
                        caption=content,
                        parse_mode=parse_mode,
                        disable_notification=disable_notification
                    )
                else:
                    message = await self.bot.send_message(
                        chat_id=chat_id,
                        text=content,
                        parse_mode=parse_mode
                    )
                    
            elif message_type == MessageType.VOICE:
                # 发送语音
                if files and files[0].get("path"):
                    with open(files[0]["path"], "rb") as voice:
                        message = await self.bot.send_voice(
                            chat_id=chat_id,
                            voice=voice,
                            caption=content,
                            parse_mode=parse_mode,
                            disable_notification=disable_notification
                        )
                elif files and files[0].get("url"):
                    message = await self.bot.send_voice(
                        chat_id=chat_id,
                        voice=files[0]["url"],
                        caption=content,
                        parse_mode=parse_mode,
                        disable_notification=disable_notification
                    )
                else:
                    message = await self.bot.send_message(
                        chat_id=chat_id,
                        text=content,
                        parse_mode=parse_mode
                    )
                    
            elif message_type == MessageType.VIDEO:
                # 发送视频
                if files and files[0].get("path"):
                    with open(files[0]["path"], "rb") as video:
                        message = await self.bot.send_video(
                            chat_id=chat_id,
                            video=video,
                            caption=content,
                            parse_mode=parse_mode,
                            disable_notification=disable_notification
                        )
                elif files and files[0].get("url"):
                    message = await self.bot.send_video(
                        chat_id=chat_id,
                        video=files[0]["url"],
                        caption=content,
                        parse_mode=parse_mode,
                        disable_notification=disable_notification
                    )
                else:
                    message = await self.bot.send_message(
                        chat_id=chat_id,
                        text=content,
                        parse_mode=parse_mode
                    )
                    
            else:
                # 不支持的消息类型，发送文本
                message = await self.bot.send_message(
                    chat_id=chat_id,
                    text=content,
                    parse_mode=parse_mode
                )
            
            return MessageResponse.success_response(
                platform=self.platform,
                chat_id=chat_id,
                message_id=str(message.message_id)
            )
            
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return MessageResponse.error_response(
                platform=self.platform,
                chat_id=chat_id,
                error=str(e)
            )
    
    async def receive_messages(self, handler: Callable[[UnifiedMessage], None]):
        """
        接收消息（轮询模式）
        
        Telegram使用长轮询模式接收消息
        """
        if not self.application:
            logger.error("Application未初始化")
            return
        
        # 注册消息处理器
        async def message_handler(update: Update, context):
            """处理收到的消息"""
            try:
                message = update.message or update.channel_post
                if not message:
                    return
                
                unified_message = self._parse_telegram_message(message)
                if unified_message:
                    await self._handle_message(unified_message)
                    
            except Exception as e:
                logger.error(f"处理Telegram消息异常: {e}")
                await self._handle_error(e)
        
        # 注册命令处理器
        async def command_handler(update: Update, context):
            """处理命令"""
            try:
                message = update.message
                if not message:
                    return
                
                # 将命令转换为消息
                unified_message = self._parse_telegram_message(message, is_command=True)
                if unified_message:
                    await self._handle_message(unified_message)
                    
            except Exception as e:
                logger.error(f"处理Telegram命令异常: {e}")
                await self._handle_error(e)
        
        # 添加处理器
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
        self.application.add_handler(CommandHandler(["start", "help", "status"], command_handler))
        
        # 注册全局处理器
        self.register_message_handler(handler)
        
        # 启动轮询
        async def start_polling():
            """启动轮询"""
            try:
                await self.application.initialize()
                await self.application.start()
                await self.application.updater.start_polling()
                
                # 保持运行
                await asyncio.Future()
                
            except asyncio.CancelledError:
                logger.info("Telegram轮询任务被取消")
            except Exception as e:
                logger.error(f"Telegram轮询异常: {e}")
        
        # 启动轮询任务
        self.polling_task = asyncio.create_task(start_polling())
        logger.info("Telegram适配器开始轮询消息")
    
    def _parse_telegram_message(self, message: TGMessage, is_command: bool = False) -> Optional[UnifiedMessage]:
        """解析Telegram消息"""
        try:
            # 获取聊天信息
            chat = message.chat
            chat_type = self._get_chat_type(chat.type)
            
            # 获取用户信息
            user = message.from_user
            user_id = str(user.id) if user else "unknown"
            username = user.username if user else None
            
            # 确定消息类型
            message_type = MessageType.TEXT
            text = message.text or message.caption or ""
            files = []
            
            # 处理不同类型的消息
            if message.photo:
                message_type = MessageType.IMAGE
                # 获取最大尺寸的图片
                photo = message.photo[-1]
                files.append(FileInfo(
                    type="image",
                    name="photo.jpg",
                    size=photo.file_size or 0,
                    mime_type="image/jpeg",
                    url=None,
                    path=None
                ))
                
            elif message.document:
                message_type = MessageType.FILE
                doc = message.document
                files.append(FileInfo(
                    type="file",
                    name=doc.file_name or "document",
                    size=doc.file_size or 0,
                    mime_type=doc.mime_type or "application/octet-stream",
                    url=None,
                    path=None
                ))
                
            elif message.voice:
                message_type = MessageType.VOICE
                voice = message.voice
                files.append(FileInfo(
                    type="voice",
                    name="voice.ogg",
                    size=voice.file_size or 0,
                    mime_type="audio/ogg",
                    url=None,
                    path=None
                ))
                
            elif message.video:
                message_type = MessageType.VIDEO
                video = message.video
                files.append(FileInfo(
                    type="video",
                    name=video.file_name or "video.mp4",
                    size=video.file_size or 0,
                    mime_type=video.mime_type or "video/mp4",
                    url=None,
                    path=None
                ))
                
            elif message.sticker:
                message_type = MessageType.STICKER
                
            elif message.location:
                message_type = MessageType.LOCATION
                text = f"位置: {message.location.latitude}, {message.location.longitude}"
            
            # 如果是命令，标记为命令类型
            if is_command or message.text.startswith('/'):
                message_type = MessageType.COMMAND
            
            # 解析提及用户
            mentions = []
            if message.entities:
                for entity in message.entities:
                    if entity.type == "mention" and entity.user:
                        mentions.append(MentionInfo(
                            user_id=str(entity.user.id),
                            username=entity.user.username,
                            display_name=entity.user.first_name or entity.user.username
                        ))
            
            # 创建统一消息对象
            unified_message = UnifiedMessage(
                platform=self.platform,
                message_id=str(message.message_id),
                chat_id=str(chat.id),
                user_id=user_id,
                username=username,
                chat_type=chat_type,
                message_type=message_type,
                text=text,
                files=files,
                mentions=mentions,
                raw_data=message.to_dict(),
                is_reply=bool(message.reply_to_message),
                is_forwarded=bool(message.forward_from or message.forward_from_chat),
                is_edited=bool(message.edit_date),
                is_deleted=False
            )
            
            return unified_message
            
        except Exception as e:
            logger.error(f"解析Telegram消息失败: {e}")
            return None
    
    def _get_chat_type(self, telegram_chat_type: str) -> ChatType:
        """转换Telegram聊天类型"""
        chat_type_map = {
            "private": ChatType.PRIVATE,
            "group": ChatType.GROUP,
            "supergroup": ChatType.SUPERGROUP,
            "channel": ChatType.CHANNEL
        }
        return chat_type_map.get(telegram_chat_type, ChatType.PRIVATE)
    
    async def upload_file(self, file_path: str, file_type: str = "file") -> Optional[str]:
        """
        上传文件到Telegram
        
        Telegram通常不需要预先上传文件，可以直接发送
        这里返回文件路径供发送时使用
        
        Args:
            file_path: 文件路径
            file_type: 文件类型
            
        Returns:
            str: 文件路径
        """
        # Telegram直接发送文件，不需要预上传
        return file_path
    
    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 用户信息
        """
        # 由于是同步方法，这里只返回基础信息
        # 实际使用时需要异步调用bot.get_chat
        return {
            "user_id": user_id,
            "platform": self.platform.value,
            "name": user_id
        }


# 注册适配器到工厂
from ..adapters.base import AdapterFactory
AdapterFactory.register(PlatformType.TELEGRAM, TelegramAdapter)