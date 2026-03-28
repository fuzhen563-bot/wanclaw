"""
QQ适配器
基于OneBot协议实现，支持多种QQ机器人框架
"""

import asyncio
import json
import logging
import websockets
from typing import Dict, List, Optional, Callable, Any
from urllib.parse import urljoin
import httpx

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


class QQAdapter(IMAdapter):
    """QQ适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(PlatformType.QQ, config)
        
        # QQ配置
        self.bot_id = config.get("bot_id")
        self.bot_secret = config.get("bot_secret")
        self.qq_number = config.get("qq_number")
        self.protocol = config.get("protocol", "onebot")  # onebot, mirai
        
        # 连接配置
        self.ws_url = config.get("ws_url", "ws://localhost:6700")
        self.http_url = config.get("http_url", "http://localhost:5700")
        self.access_token = config.get("access_token")
        
        # WebSocket连接
        self.ws_connection = None
        self.ws_task = None
        
        # HTTP客户端
        self.http_client = None
        
        if not any([self.ws_url, self.http_url]):
            raise ValueError("QQ配置需要至少指定 ws_url 或 http_url")
    
    async def connect(self) -> bool:
        """连接到QQ机器人服务"""
        try:
            # 初始化HTTP客户端
            headers = {}
            if self.access_token:
                headers["Authorization"] = f"Bearer {self.access_token}"
            
            self.http_client = httpx.AsyncClient(headers=headers)
            
            # 测试HTTP连接
            if self.http_url:
                try:
                    response = await self.http_client.get(f"{self.http_url}/get_status")
                    if response.status_code == 200:
                        logger.info(f"QQ HTTP连接成功: {self.http_url}")
                    else:
                        logger.warning(f"QQ HTTP连接测试失败: {response.status_code}")
                except Exception as e:
                    logger.warning(f"QQ HTTP连接测试异常: {e}")
            
            # 尝试WebSocket连接
            if self.ws_url:
                try:
                    ws_headers = {}
                    if self.access_token:
                        ws_headers["Authorization"] = f"Bearer {self.access_token}"
                    
                    self.ws_connection = await websockets.connect(
                        self.ws_url,
                        extra_headers=ws_headers
                    )
                    logger.info(f"QQ WebSocket连接成功: {self.ws_url}")
                except Exception as e:
                    logger.warning(f"QQ WebSocket连接失败: {e}")
                    self.ws_connection = None
            
            self._connected = True
            self._stats["last_connected"] = asyncio.get_event_loop().time()
            logger.info(f"QQ适配器连接成功，协议: {self.protocol}")
            return True
            
        except Exception as e:
            logger.error(f"QQ适配器连接失败: {e}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        # 关闭WebSocket连接
        if self.ws_connection:
            await self.ws_connection.close()
            self.ws_connection = None
        
        # 取消WebSocket任务
        if self.ws_task:
            self.ws_task.cancel()
            try:
                await self.ws_task
            except asyncio.CancelledError:
                pass
            self.ws_task = None
        
        # 关闭HTTP客户端
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
        
        self._connected = False
        logger.info("QQ适配器已断开")
    
    async def _make_http_request(self, action: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """发送HTTP请求到QQ机器人API"""
        if not self.http_url or not self.http_client:
            return None
        
        url = f"{self.http_url}/{action}"
        
        try:
            response = await self.http_client.post(url, json=params or {})
            response.raise_for_status()
            
            data = response.json()
            if data.get("status") == "ok" or data.get("retcode") == 0:
                return data.get("data")
            else:
                logger.error(f"QQ API请求失败: {data}")
                return None
        except Exception as e:
            logger.error(f"QQ API请求异常: {e}")
            return None
    
    async def send_message(
        self,
        chat_id: str,
        content: str,
        message_type: MessageType = MessageType.TEXT,
        files: Optional[List[Dict]] = None,
        **kwargs
    ) -> MessageResponse:
        """
        发送消息到QQ
        
        QQ支持的消息类型:
        - text: 文本消息
        - image: 图片消息
        - voice: 语音消息
        - file: 文件消息
        - markdown: Markdown消息
        - json: JSON消息
        """
        try:
            # 判断消息类型
            msg_type = message_type.value
            
            # 构建API参数
            params = {
                "message_type": "private" if chat_id.isdigit() else "group",
                "user_id" if chat_id.isdigit() else "group_id": int(chat_id),
                "auto_escape": kwargs.get("auto_escape", False)
            }
            
            # 构建消息内容
            if msg_type == "text":
                params["message"] = content
                
            elif msg_type == "image":
                # 图片消息
                image_content = ""
                if files and files[0].get("path"):
                    # 本地文件
                    image_content = f"file://{files[0]['path']}"
                elif files and files[0].get("url"):
                    # 网络图片
                    image_content = files[0]["url"]
                else:
                    image_content = content
                
                params["message"] = f"[CQ:image,file={image_content}]"
                
            elif msg_type == "voice":
                # 语音消息
                voice_content = ""
                if files and files[0].get("path"):
                    voice_content = f"file://{files[0]['path']}"
                elif files and files[0].get("url"):
                    voice_content = files[0]["url"]
                
                if voice_content:
                    params["message"] = f"[CQ:record,file={voice_content}]"
                else:
                    params["message"] = content
                    
            elif msg_type == "file":
                # 文件消息
                file_content = ""
                if files and files[0].get("path"):
                    file_content = f"file://{files[0]['path']}"
                elif files and files[0].get("url"):
                    file_content = files[0]["url"]
                
                if file_content:
                    params["message"] = f"[CQ:file,file={file_content}]"
                else:
                    params["message"] = content
            
            else:
                # 其他类型使用文本消息
                params["message"] = content
            
            # 发送消息
            result = await self._make_http_request("send_msg", params)
            if not result:
                return MessageResponse.error_response(
                    platform=self.platform,
                    chat_id=chat_id,
                    error="API请求失败"
                )
            
            message_id = result.get("message_id")
            return MessageResponse.success_response(
                platform=self.platform,
                chat_id=chat_id,
                message_id=str(message_id) if message_id else "unknown"
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
        接收消息（WebSocket模式）
        
        QQ机器人通常使用WebSocket接收事件
        """
        if not self.ws_connection:
            logger.warning("WebSocket连接未建立，无法接收消息")
            return
        
        # 类型提示，确保ws_connection不是None
        ws_connection = self.ws_connection
        
        async def ws_listener():
            """WebSocket监听器"""
            try:
                async for message in ws_connection:
                    try:
                        data = json.loads(message)
                        event_type = data.get("post_type")
                        
                        if event_type == "message":
                            # 消息事件
                            unified_message = self._parse_websocket_message(data)
                            if unified_message:
                                await self._handle_message(unified_message)
                                
                        elif event_type == "notice":
                            # 通知事件
                            notice_type = data.get("notice_type")
                            if notice_type == "group_increase":
                                # 群成员增加
                                logger.info(f"新成员加入群: {data.get('group_id')}")
                                
                        elif event_type == "request":
                            # 请求事件
                            request_type = data.get("request_type")
                            logger.debug(f"收到请求: {request_type}")
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"解析WebSocket消息失败: {e}")
                    except Exception as e:
                        logger.error(f"处理WebSocket消息异常: {e}")
                        await self._handle_error(e)
                        
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket连接已关闭")
            except Exception as e:
                logger.error(f"WebSocket监听异常: {e}")
                await self._handle_error(e)
        
        # 启动WebSocket监听任务
        self.ws_task = asyncio.create_task(ws_listener())
        
        # 注册消息处理器
        self.register_message_handler(handler)
        
        logger.info("QQ适配器开始监听WebSocket消息")
    
    def _parse_websocket_message(self, data: Dict) -> Optional[UnifiedMessage]:
        """解析WebSocket消息"""
        try:
            # 获取消息基本信息
            message_type = data.get("message_type")  # private, group
            sub_type = data.get("sub_type")  # friend, group, discuss, etc.
            message_id = data.get("message_id")
            raw_message = data.get("raw_message", "")
            message_seq = data.get("message_seq")
            
            # 获取发送者信息
            user_id = str(data.get("user_id", ""))
            sender = data.get("sender", {})
            nickname = sender.get("nickname", "")
            
            # 获取聊天信息
            if message_type == "private":
                chat_id = user_id
                chat_type = ChatType.PRIVATE
            elif message_type == "group":
                chat_id = str(data.get("group_id", ""))
                chat_type = ChatType.GROUP
            else:
                # 其他类型暂不支持
                return None
            
            # 解析CQ码消息
            parsed_content = self._parse_cq_code(raw_message)
            text = parsed_content["text"]
            files = parsed_content["files"]
            
            # 判断是否为命令
            is_command = text.startswith('/') if text else False
            
            # 创建统一消息对象
            unified_message = UnifiedMessage(
                platform=self.platform,
                message_id=str(message_id) if message_id else str(message_seq),
                chat_id=chat_id,
                user_id=user_id,
                username=nickname,
                chat_type=chat_type,
                message_type=MessageType.COMMAND if is_command else MessageType.TEXT,
                text=text,
                files=files,
                raw_data=data,
                is_reply=False,  # 需要解析reply消息
                is_forwarded=False,
                is_edited=False,
                is_deleted=False
            )
            
            return unified_message
            
        except Exception as e:
            logger.error(f"解析WebSocket消息失败: {e}")
            return None
    
    def _parse_cq_code(self, raw_message: str) -> Dict[str, Any]:
        """解析CQ码消息"""
        text = ""
        files = []
        
        # 简单的CQ码解析
        import re
        
        # 匹配CQ码
        cq_pattern = r'\[CQ:(\w+)(?:,([^\]]+))?\]'
        
        # 替换CQ码为文本表示
        def replace_cq(match):
            cq_type = match.group(1)
            params_str = match.group(2) or ""
            
            # 解析参数
            params = {}
            if params_str:
                for param in params_str.split(','):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        params[key] = value
            
            if cq_type == "image":
                # 图片消息
                file_url = params.get("url", params.get("file", ""))
                files.append(FileInfo(
                    type="image",
                    url=file_url,
                    name="image.jpg",
                    path=None,
                    size=0,
                    mime_type="image/jpeg"
                ))
                return "[图片]"
                
            elif cq_type == "record":
                # 语音消息
                file_url = params.get("file", "")
                files.append(FileInfo(
                    type="voice",
                    url=file_url,
                    name="voice.amr",
                    path=None,
                    size=0,
                    mime_type="audio/amr"
                ))
                return "[语音]"
                
            elif cq_type == "file":
                # 文件消息
                file_name = params.get("name", "file")
                file_url = params.get("file", "")
                files.append(FileInfo(
                    type="file",
                    url=file_url,
                    name=file_name,
                    path=None,
                    size=int(params.get("size", 0)),
                    mime_type="application/octet-stream"
                ))
                return f"[文件:{file_name}]"
                
            elif cq_type == "at":
                # @某人
                qq_id = params.get("qq", "")
                return f"@{qq_id}"
                
            elif cq_type == "face":
                # 表情
                face_id = params.get("id", "")
                return f"[表情:{face_id}]"
                
            else:
                # 其他CQ码
                return f"[{cq_type}]"
        
        # 替换所有CQ码
        text = re.sub(cq_pattern, replace_cq, raw_message)
        
        return {
            "text": text.strip(),
            "files": files
        }
    
    async def upload_file(self, file_path: str, file_type: str = "file") -> Optional[str]:
        """
        上传文件到QQ
        
        Args:
            file_path: 文件路径
            file_type: 文件类型
            
        Returns:
            str: 文件URL或文件ID
        """
        # QQ机器人通常支持本地文件路径直接发送
        # 如果需要上传到网络，这里需要实现具体逻辑
        return f"file://{file_path}"
    
    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 用户信息
        """
        # 由于是同步方法，这里只返回基础信息
        return {
            "user_id": user_id,
            "platform": self.platform.value,
            "name": user_id
        }


# 注册适配器到工厂
from ..adapters.base import AdapterFactory
AdapterFactory.register(PlatformType.QQ, QQAdapter)