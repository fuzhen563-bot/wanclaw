"""
微信适配器
基于微信开放平台和企业微信接口实现
支持多种微信机器人方案
"""

import asyncio
import json
import logging
import time
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


class WeChatAdapter(IMAdapter):
    """微信适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(PlatformType.WECHAT, config)
        
        # 微信配置
        self.wechat_type = config.get("type", "work")  # work:企业微信, official:公众号, thirdparty:第三方
        self.app_id = config.get("app_id")
        self.app_secret = config.get("app_secret")
        self.corp_id = config.get("corp_id")  # 企业微信需要
        self.agent_id = config.get("agent_id")  # 企业微信需要
        
        # 第三方机器人配置
        self.thirdparty_url = config.get("thirdparty_url")
        self.thirdparty_token = config.get("thirdparty_token")
        
        # API配置
        self.base_url = "https://api.weixin.qq.com"
        if self.wechat_type == "work":
            self.base_url = "https://qyapi.weixin.qq.com"
        
        self.access_token = None
        self.token_expires_at = None
        
        # HTTP客户端
        self.http_client = None
        
        # 消息接收服务器
        self.webhook_url = config.get("webhook_url")
        
        if self.wechat_type == "work" and not all([self.corp_id, self.agent_id, self.app_secret]):
            raise ValueError("企业微信配置需要 corp_id, agent_id, app_secret")
        elif self.wechat_type == "official" and not all([self.app_id, self.app_secret]):
            raise ValueError("公众号配置需要 app_id, app_secret")
        elif self.wechat_type == "thirdparty" and not self.thirdparty_url:
            raise ValueError("第三方机器人需要 thirdparty_url")
    
    async def _get_access_token(self) -> Optional[str]:
        """获取access_token"""
        if self.access_token and self.token_expires_at and self.token_expires_at > asyncio.get_event_loop().time():
            return self.access_token
        
        try:
            if self.wechat_type == "work":
                # 企业微信获取token
                url = f"{self.base_url}/cgi-bin/gettoken"
                params = {
                    "corpid": self.corp_id,
                    "corpsecret": self.app_secret
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    
                    data = response.json()
                    if data.get("errcode") == 0:
                        self.access_token = data["access_token"]
                        self.token_expires_at = asyncio.get_event_loop().time() + data.get("expires_in", 7200) - 300
                        return self.access_token
                    else:
                        logger.error(f"获取企业微信access_token失败: {data}")
                        return None
                        
            elif self.wechat_type == "official":
                # 公众号获取token
                url = f"{self.base_url}/cgi-bin/token"
                params = {
                    "grant_type": "client_credential",
                    "appid": self.app_id,
                    "secret": self.app_secret
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    
                    data = response.json()
                    if "access_token" in data:
                        self.access_token = data["access_token"]
                        self.token_expires_at = asyncio.get_event_loop().time() + data.get("expires_in", 7200) - 300
                        return self.access_token
                    else:
                        logger.error(f"获取公众号access_token失败: {data}")
                        return None
                        
            else:
                # 第三方机器人不需要token
                return "thirdparty"
                
        except Exception as e:
            logger.error(f"获取access_token异常: {e}")
            return None
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """发送请求到微信API"""
        if self.wechat_type == "thirdparty":
            # 第三方机器人直接请求
            url = f"{self.thirdparty_url}/{endpoint}"
        else:
            # 官方API需要token
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
                
                if self.wechat_type == "work":
                    if data.get("errcode") == 0:
                        return data
                    else:
                        logger.error(f"企业微信API请求失败: {data}")
                        return None
                elif self.wechat_type == "official":
                    if "errcode" in data and data["errcode"] != 0:
                        logger.error(f"公众号API请求失败: {data}")
                        return None
                    return data
                else:
                    # 第三方机器人
                    return data
                    
        except Exception as e:
            logger.error(f"微信API请求异常: {e}")
            return None
    
    async def connect(self) -> bool:
        """连接到微信"""
        try:
            # 测试获取access_token
            if self.wechat_type != "thirdparty":
                token = await self._get_access_token()
                if not token:
                    return False
            
            # 初始化HTTP客户端
            self.http_client = httpx.AsyncClient()
            
            self._connected = True
            self._stats["last_connected"] = asyncio.get_event_loop().time()
            logger.info(f"微信适配器连接成功，类型: {self.wechat_type}")
            return True
            
        except Exception as e:
            logger.error(f"微信适配器连接失败: {e}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
        
        self._connected = False
        logger.info("微信适配器已断开")
    
    async def send_message(
        self,
        chat_id: str,
        content: str,
        message_type: MessageType = MessageType.TEXT,
        files: Optional[List[Dict]] = None,
        **kwargs
    ) -> MessageResponse:
        """
        发送消息到微信
        
        微信支持的消息类型取决于类型:
        - work: 文本、图片、语音、视频、文件、图文等
        - official: 客服消息、模板消息
        - thirdparty: 依赖具体实现
        """
        try:
            if self.wechat_type == "work":
                # 企业微信发送消息
                return await self._send_work_message(chat_id, content, message_type, files, kwargs)
            elif self.wechat_type == "official":
                # 公众号发送消息
                return await self._send_official_message(chat_id, content, message_type, files, kwargs)
            else:
                # 第三方机器人发送消息
                return await self._send_thirdparty_message(chat_id, content, message_type, files, kwargs)
                
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return MessageResponse.error_response(
                platform=self.platform,
                chat_id=chat_id,
                error=str(e)
            )
    
    async def _send_work_message(self, chat_id: str, content: str, message_type: MessageType,
                                files: Optional[List[Dict]], kwargs: Dict) -> MessageResponse:
        """发送企业微信消息"""
        # 构建消息体
        msg_type = message_type.value
        
        if msg_type == "text":
            msg_data = {
                "touser": chat_id,
                "msgtype": "text",
                "agentid": self.agent_id,
                "text": {"content": content}
            }
        elif msg_type == "image":
            # 需要先上传图片
            media_id = kwargs.get("media_id")
            if media_id:
                msg_data = {
                    "touser": chat_id,
                    "msgtype": "image",
                    "agentid": self.agent_id,
                    "image": {"media_id": media_id}
                }
            else:
                return MessageResponse.error_response(
                    platform=self.platform,
                    chat_id=chat_id,
                    error="图片消息需要media_id"
                )
        else:
            # 其他类型暂用文本消息
            msg_data = {
                "touser": chat_id,
                "msgtype": "text",
                "agentid": self.agent_id,
                "text": {"content": f"[{msg_type}] {content}"}
            }
        
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
    
    async def _send_official_message(self, chat_id: str, content: str, message_type: MessageType,
                                   files: Optional[List[Dict]], kwargs: Dict) -> MessageResponse:
        """发送公众号消息（客服消息）"""
        # 公众号通常通过客服接口发送消息
        msg_type = message_type.value
        
        if msg_type == "text":
            msg_data = {
                "touser": chat_id,
                "msgtype": "text",
                "text": {"content": content}
            }
        elif msg_type == "image":
            media_id = kwargs.get("media_id")
            if media_id:
                msg_data = {
                    "touser": chat_id,
                    "msgtype": "image",
                    "image": {"media_id": media_id}
                }
            else:
                return MessageResponse.error_response(
                    platform=self.platform,
                    chat_id=chat_id,
                    error="图片消息需要media_id"
                )
        else:
            # 其他类型暂用文本消息
            msg_data = {
                "touser": chat_id,
                "msgtype": "text",
                "text": {"content": f"[{msg_type}] {content}"}
            }
        
        # 发送客服消息
        result = await self._make_request("POST", "cgi-bin/message/custom/send", json=msg_data)
        if not result:
            return MessageResponse.error_response(
                platform=self.platform,
                chat_id=chat_id,
                error="API请求失败"
            )
        
        return MessageResponse.success_response(
            platform=self.platform,
            chat_id=chat_id,
            message_id=str(int(time.time()))  # 公众号没有message_id，使用时间戳
        )
    
    async def _send_thirdparty_message(self, chat_id: str, content: str, message_type: MessageType,
                                      files: Optional[List[Dict]], kwargs: Dict) -> MessageResponse:
        """发送第三方机器人消息"""
        # 第三方机器人API格式各不相同
        # 这里假设一个通用的JSON格式
        
        msg_data = {
            "to": chat_id,
            "type": message_type.value,
            "content": content,
            "files": files or []
        }
        
        # 添加认证头
        headers = {}
        if self.thirdparty_token:
            headers["Authorization"] = f"Bearer {self.thirdparty_token}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.thirdparty_url}/send_message",
                    json=msg_data,
                    headers=headers
                )
                response.raise_for_status()
                
                data = response.json()
                if data.get("success"):
                    return MessageResponse.success_response(
                        platform=self.platform,
                        chat_id=chat_id,
                        message_id=data.get("message_id", "unknown")
                    )
                else:
                    return MessageResponse.error_response(
                        platform=self.platform,
                        chat_id=chat_id,
                        error=data.get("error", "发送失败")
                    )
                    
        except Exception as e:
            return MessageResponse.error_response(
                platform=self.platform,
                chat_id=chat_id,
                error=str(e)
            )
    
    async def receive_messages(self, handler: Callable[[UnifiedMessage], None]):
        """
        接收消息（回调模式）
        
        微信使用回调模式，需要配置服务器和验证
        """
        # 微信需要配置服务器接收回调
        # 这里提供回调处理框架
        
        async def callback_handler(request):
            """回调处理器"""
            try:
                # 获取请求数据
                data = await request.json()
                logger.debug(f"收到微信回调: {data}")
                
                # 验证消息签名（如果有）
                if self.wechat_type == "work":
                    # 企业微信回调验证
                    msg_signature = request.headers.get("msg_signature")
                    timestamp = request.headers.get("timestamp")
                    nonce = request.headers.get("nonce")
                    
                    # 这里需要实现签名验证
                
                # 解析消息
                message = self._parse_callback_message(data)
                if message:
                    await self._handle_message(message)
                
                # 返回成功响应
                return {"errcode": 0, "errmsg": "ok"}
                
            except Exception as e:
                logger.error(f"处理回调异常: {e}")
                return {"errcode": 500, "errmsg": "internal error"}
        
        logger.info(f"微信适配器使用回调模式，类型: {self.wechat_type}")
        
        # 注册处理器
        self.register_message_handler(handler)
    
    def _parse_callback_message(self, data: Dict) -> Optional[UnifiedMessage]:
        """解析微信回调消息"""
        try:
            if self.wechat_type == "work":
                # 解析企业微信消息
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
                
            elif self.wechat_type == "official":
                # 解析公众号消息
                msg_type = data.get("MsgType", "")
                from_user = data.get("FromUserName", "")
                to_user = data.get("ToUserName", "")
                msg_id = data.get("MsgId", "")
                
                text = ""
                if msg_type == "text":
                    text = data.get("Content", "")
                
                message = UnifiedMessage(
                    platform=self.platform,
                    message_id=msg_id,
                    chat_id=from_user,
                    user_id=from_user,
                    username=from_user,
                    chat_type=ChatType.PRIVATE,
                    message_type=MessageType(msg_type),
                    text=text,
                    files=[],
                    raw_data=data,
                    is_reply=False,
                    is_forwarded=False,
                    is_edited=False,
                    is_deleted=False
                )
                
                return message
                
            else:
                # 第三方机器人消息格式
                # 假设一个通用格式
                message = UnifiedMessage(
                    platform=self.platform,
                    message_id=data.get("id", ""),
                    chat_id=data.get("chat_id", ""),
                    user_id=data.get("user_id", ""),
                    username=data.get("username", ""),
                    chat_type=ChatType.PRIVATE,
                    message_type=MessageType(data.get("type", "text")),
                    text=data.get("content", ""),
                    files=[],
                    raw_data=data,
                    is_reply=False,
                    is_forwarded=False,
                    is_edited=False,
                    is_deleted=False
                )
                
                return message
                
        except Exception as e:
            logger.error(f"解析微信回调消息失败: {e}")
            return None
    
    async def upload_file(self, file_path: str, file_type: str = "file") -> Optional[str]:
        """
        上传文件到微信
        
        Args:
            file_path: 文件路径
            file_type: 文件类型
            
        Returns:
            str: media_id
        """
        if self.wechat_type == "thirdparty":
            # 第三方机器人可能有自己的上传接口
            return f"file://{file_path}"
        
        try:
            token = await self._get_access_token()
            if not token:
                return None
            
            if self.wechat_type == "work":
                url = f"{self.base_url}/cgi-bin/media/upload"
            else:
                url = f"{self.base_url}/cgi-bin/media/upload"
            
            params = {
                "access_token": token,
                "type": file_type
            }
            
            with open(file_path, "rb") as f:
                files = {"media": f}
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, params=params, files=files)
                    response.raise_for_status()
                    
                    data = response.json()
                    if (self.wechat_type == "work" and data.get("errcode") == 0) or \
                       (self.wechat_type == "official" and "media_id" in data):
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
        return {
            "user_id": user_id,
            "platform": self.platform.value,
            "type": self.wechat_type,
            "name": user_id
        }


# 注册适配器到工厂
from ..adapters.base import AdapterFactory
AdapterFactory.register(PlatformType.WECHAT, WeChatAdapter)