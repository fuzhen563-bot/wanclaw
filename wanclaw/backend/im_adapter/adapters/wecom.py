"""
企业微信适配器
基于企业微信开放API实现
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Callable, Any
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


class WeComAdapter(IMAdapter):
    """企业微信适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(PlatformType.WECOM, config)
        
        # 企业微信配置
        self.corp_id = config.get("corp_id")
        self.agent_id = config.get("agent_id")
        self.secret = config.get("secret")
        
        # API配置
        self.base_url = "https://qyapi.weixin.qq.com/cgi-bin"
        self.access_token = None
        self.token_expires_at = None
        
        # HTTP客户端
        self.http_client = None
        
        # 消息接收
        self.webhook_url = config.get("webhook_url")
        self.webhook_server = None
        
        if not all([self.corp_id, self.agent_id, self.secret]):
            raise ValueError("企业微信配置不完整，需要 corp_id, agent_id, secret")
    
    async def _get_access_token(self) -> Optional[str]:
        """获取access_token"""
        if self.access_token and self.token_expires_at and self.token_expires_at > asyncio.get_event_loop().time():
            return self.access_token
        
        url = f"{self.base_url}/gettoken"
        params = {
            "corpid": self.corp_id,
            "corpsecret": self.secret
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                if data.get("errcode") == 0:
                    self.access_token = data["access_token"]
                    # 提前5分钟刷新
                    self.token_expires_at = asyncio.get_event_loop().time() + data.get("expires_in", 7200) - 300
                    logger.info(f"获取企业微信access_token成功")
                    return self.access_token
                else:
                    logger.error(f"获取access_token失败: {data}")
                    return None
        except Exception as e:
            logger.error(f"获取access_token异常: {e}")
            return None
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """发送请求到企业微信API"""
        token = await self._get_access_token()
        if not token:
            return None
        
        url = f"{self.base_url}/{endpoint}"
        params = kwargs.get("params", {})
        params["access_token"] = token
        
        try:
            async with httpx.AsyncClient() as client:
                if method.upper() == "GET":
                    response = await client.get(url, params=params)
                else:
                    # POST请求
                    json_data = kwargs.get("json")
                    if json_data:
                        response = await client.post(url, params=params, json=json_data)
                    else:
                        response = await client.post(url, params=params, data=kwargs.get("data"))
                
                response.raise_for_status()
                data = response.json()
                
                if data.get("errcode") == 0:
                    return data
                else:
                    logger.error(f"企业微信API请求失败: {data}")
                    return None
        except Exception as e:
            logger.error(f"企业微信API请求异常: {e}")
            return None
    
    async def connect(self) -> bool:
        """连接到企业微信"""
        try:
            # 测试获取access_token
            token = await self._get_access_token()
            if not token:
                return False
            
            # 初始化HTTP客户端
            self.http_client = httpx.AsyncClient()
            
            # 如果需要，可以在这里启动Webhook服务器
            # 企业微信通常使用回调模式，需要公网可访问的URL
            
            self._connected = True
            self._stats["last_connected"] = asyncio.get_event_loop().time()
            logger.info(f"企业微信适配器连接成功")
            return True
            
        except Exception as e:
            logger.error(f"企业微信适配器连接失败: {e}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
        
        self._connected = False
        logger.info("企业微信适配器已断开")
    
    async def send_message(
        self,
        chat_id: str,
        content: str,
        message_type: MessageType = MessageType.TEXT,
        files: Optional[List[Dict]] = None,
        **kwargs
    ) -> MessageResponse:
        """
        发送消息到企业微信
        
        企业微信支持的消息类型:
        - text: 文本消息
        - image: 图片消息
        - voice: 语音消息
        - video: 视频消息
        - file: 文件消息
        - textcard: 文本卡片消息
        - news: 图文消息
        - mpnews: 图文消息(mpnews)
        - markdown: markdown消息
        """
        try:
            # 构建消息体
            if chat_id.startswith("@"):  # 用户ID
                msg_data = self._build_user_message(chat_id, content, message_type, files, kwargs)
            else:  # 群聊ID
                msg_data = self._build_group_message(chat_id, content, message_type, files, kwargs)
            
            if not msg_data:
                return MessageResponse.error_response(
                    platform=self.platform,
                    chat_id=chat_id,
                    error="构建消息失败"
                )
            
            # 发送消息
            result = await self._make_request("POST", "message/send", json=msg_data)
            if not result:
                return MessageResponse.error_response(
                    platform=self.platform,
                    chat_id=chat_id,
                    error="API请求失败"
                )
            
            message_id = result.get("msgid")
            return MessageResponse.success_response(
                platform=self.platform,
                chat_id=chat_id,
                message_id=message_id or "unknown"
            )
            
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return MessageResponse.error_response(
                platform=self.platform,
                chat_id=chat_id,
                error=str(e)
            )
    
    def _build_user_message(self, user_id: str, content: str, message_type: MessageType, 
                           files: Optional[List[Dict]], kwargs: Dict) -> Optional[Dict]:
        """构建发送给用户的消息"""
        msg_type = message_type.value
        
        # 基础消息结构
        msg_data = {
            "touser": user_id.lstrip("@"),
            "msgtype": msg_type,
            "agentid": self.agent_id,
            "safe": kwargs.get("safe", 0),  # 0:不保密, 1:保密消息
            "enable_id_trans": kwargs.get("enable_id_trans", 0),  # 是否开启id转译
            "enable_duplicate_check": kwargs.get("enable_duplicate_check", 0),  # 是否重复消息检查
        }
        
        # 根据消息类型构建内容
        if msg_type == "text":
            msg_data["text"] = {"content": content}
            
        elif msg_type == "markdown":
            msg_data["markdown"] = {"content": content}
            
        elif msg_type == "image":
            # 需要先上传图片获取media_id
            media_id = kwargs.get("media_id")
            if media_id:
                msg_data["image"] = {"media_id": media_id}
            else:
                logger.error("图片消息需要media_id")
                return None
                
        elif msg_type == "file":
            media_id = kwargs.get("media_id")
            if media_id:
                msg_data["file"] = {"media_id": media_id}
            else:
                logger.error("文件消息需要media_id")
                return None
                
        elif msg_type == "textcard":
            # 文本卡片消息
            title = kwargs.get("title", "通知")
            description = kwargs.get("description", content)
            url = kwargs.get("url", "")
            btntxt = kwargs.get("btntxt", "详情")
            
            msg_data["textcard"] = {
                "title": title,
                "description": description,
                "url": url,
                "btntxt": btntxt
            }
            
        else:
            logger.warning(f"暂不支持的消息类型: {msg_type}")
            return None
        
        return msg_data
    
    def _build_group_message(self, chat_id: str, content: str, message_type: MessageType,
                            files: Optional[List[Dict]], kwargs: Dict) -> Optional[Dict]:
        """构建发送给群聊的消息"""
        # 企业微信中，群聊通过chatid标识
        msg_data = self._build_user_message("@all", content, message_type, files, kwargs)
        if msg_data:
            msg_data["touser"] = ""
            msg_data["toparty"] = ""
            msg_data["totag"] = ""
            msg_data["chatid"] = chat_id
        return msg_data
    
    async def receive_messages(self, handler: Callable[[UnifiedMessage], None]):
        """
        接收消息（回调模式）
        
        企业微信使用回调模式，需要配置可信域名和接收服务器
        这里提供一个基础的Webhook服务器示例
        """
        # 这里应该启动一个Webhook服务器来接收企业微信的回调
        # 由于需要公网可访问的URL，这里只提供框架代码
        
        async def webhook_handler(request):
            """Webhook处理器"""
            try:
                data = await request.json()
                logger.debug(f"收到企业微信回调: {data}")
                
                # 解析消息
                message = self._parse_callback_message(data)
                if message:
                    await self._handle_message(message)
                
                # 返回成功响应（企业微信要求）
                return {"errcode": 0, "errmsg": "ok"}
                
            except Exception as e:
                logger.error(f"处理Webhook异常: {e}")
                return {"errcode": 500, "errmsg": "internal error"}
        
        # 在实际部署中，这里应该启动一个Web服务器
        # 例如使用FastAPI或aiohttp
        logger.info("企业微信适配器使用回调模式，需要配置Webhook服务器")
        
        # 注册处理器
        self.register_message_handler(handler)
    
    def _parse_callback_message(self, data: Dict) -> Optional[UnifiedMessage]:
        """解析企业微信回调消息"""
        try:
            msg_type = data.get("MsgType", "")
            from_user = data.get("FromUserName", "")
            to_user = data.get("ToUserName", "")
            msg_id = data.get("MsgId", "")
            
            # 判断是否为群聊
            chat_type = ChatType.GROUP if "@chatroom" in from_user else ChatType.PRIVATE
            
            # 提取消息内容
            text = ""
            files = []
            
            if msg_type == "text":
                text = data.get("Content", "")
            elif msg_type == "image":
                text = data.get("PicUrl", "")
                files.append(FileInfo(
                    type="image",
                    url=data.get("PicUrl", ""),
                    name="image.jpg",
                    path=None,
                    size=0,
                    mime_type="image/jpeg"
                ))
            elif msg_type == "voice":
                text = "语音消息"
                files.append(FileInfo(
                    type="voice",
                    url=None,
                    path=None,
                    name="voice.mp3",
                    size=0,
                    mime_type="audio/mp3"
                ))
            elif msg_type == "video":
                text = "视频消息"
                files.append(FileInfo(
                    type="video",
                    url=None,
                    path=None,
                    name="video.mp4",
                    size=0,
                    mime_type="video/mp4"
                ))
            elif msg_type == "file":
                text = data.get("FileName", "")
                files.append(FileInfo(
                    type="file",
                    url=None,
                    path=None,
                    name=data.get("FileName", ""),
                    size=0,
                    mime_type="application/octet-stream"
                ))
            
            # 创建统一消息对象
            message = UnifiedMessage(
                platform=self.platform,
                message_id=msg_id,
                chat_id=from_user,
                user_id=from_user,
                username=from_user,
                chat_type=chat_type,
                message_type=MessageType(msg_type),
                text=text,
                files=files,
                raw_data=data,
                is_reply=False,
                is_forwarded=False,
                is_edited=False,
                is_deleted=False
            )
            
            return message
            
        except Exception as e:
            logger.error(f"解析回调消息失败: {e}")
            return None
    
    async def upload_file(self, file_path: str, file_type: str = "file") -> Optional[str]:
        """
        上传文件到企业微信
        
        Args:
            file_path: 文件路径
            file_type: 文件类型 (image, voice, video, file)
            
        Returns:
            str: media_id
        """
        try:
            token = await self._get_access_token()
            if not token:
                return None
            
            url = f"{self.base_url}/media/upload"
            params = {
                "access_token": token,
                "type": file_type
            }
            
            # 读取文件
            with open(file_path, "rb") as f:
                files = {"media": f}
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, params=params, files=files)
                    response.raise_for_status()
                    
                    data = response.json()
                    if data.get("errcode") == 0:
                        media_id = data.get("media_id")
                        logger.info(f"文件上传成功: {file_path} -> {media_id}")
                        return media_id
                    else:
                        logger.error(f"文件上传失败: {data}")
                        return None
                        
        except Exception as e:
            logger.error(f"文件上传异常: {e}")
            return None
    
    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        获取用户信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict: 用户信息
        """
        # 企业微信获取用户信息API
        # 由于是同步方法，这里只返回基础信息
        return {
            "user_id": user_id,
            "platform": self.platform.value,
            "name": user_id  # 实际应该调用API获取
        }


# 注册适配器到工厂
from ..adapters.base import AdapterFactory
AdapterFactory.register(PlatformType.WECOM, WeComAdapter)