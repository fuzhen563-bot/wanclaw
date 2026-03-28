"""
飞书适配器
基于飞书开放平台API实现
"""

import asyncio
import json
import logging
import hmac
import hashlib
import base64
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


class FeishuAdapter(IMAdapter):
    """飞书适配器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(PlatformType.FEISHU, config)
        
        # 飞书配置
        self.app_id = config.get("app_id")
        self.app_secret = config.get("app_secret")
        self.verification_token = config.get("verification_token")
        self.encrypt_key = config.get("encrypt_key")
        
        # API配置
        self.base_url = "https://open.feishu.cn/open-apis"
        self.tenant_access_token = None
        self.token_expires_at = None
        
        # HTTP客户端
        self.http_client = None
        
        # 事件订阅
        self.webhook_url = config.get("webhook_url")
        
        if not all([self.app_id, self.app_secret]):
            raise ValueError("飞书配置不完整，需要 app_id, app_secret")
    
    async def _get_tenant_access_token(self) -> Optional[str]:
        """获取tenant_access_token"""
        if self.tenant_access_token and self.token_expires_at and self.token_expires_at > asyncio.get_event_loop().time():
            return self.tenant_access_token
        
        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                data = response.json()
                if data.get("code") == 0:
                    self.tenant_access_token = data["tenant_access_token"]
                    # 提前5分钟刷新
                    self.token_expires_at = asyncio.get_event_loop().time() + data.get("expire", 7200) - 300
                    logger.info(f"获取飞书tenant_access_token成功")
                    return self.tenant_access_token
                else:
                    logger.error(f"获取tenant_access_token失败: {data}")
                    return None
        except Exception as e:
            logger.error(f"获取tenant_access_token异常: {e}")
            return None
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """发送请求到飞书API"""
        token = await self._get_tenant_access_token()
        if not token:
            return None
        
        url = f"{self.base_url}/{endpoint}"
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        
        try:
            async with httpx.AsyncClient() as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers, params=kwargs.get("params"))
                else:
                    # POST请求
                    json_data = kwargs.get("json")
                    if json_data:
                        response = await client.post(url, headers=headers, json=json_data)
                    else:
                        response = await client.post(url, headers=headers, data=kwargs.get("data"))
                
                response.raise_for_status()
                data = response.json()
                
                if data.get("code") == 0:
                    return data.get("data")
                else:
                    logger.error(f"飞书API请求失败: {data}")
                    return None
        except Exception as e:
            logger.error(f"飞书API请求异常: {e}")
            return None
    
    async def connect(self) -> bool:
        """连接到飞书"""
        try:
            # 测试获取tenant_access_token
            token = await self._get_tenant_access_token()
            if not token:
                return False
            
            # 初始化HTTP客户端
            self.http_client = httpx.AsyncClient()
            
            # 测试API连通性
            result = await self._make_request("GET", "auth/v3/app_access_token/internal/")
            if not result:
                logger.warning("飞书API测试失败")
                # 继续连接，有些API可能需要额外权限
            
            self._connected = True
            self._stats["last_connected"] = asyncio.get_event_loop().time()
            logger.info(f"飞书适配器连接成功")
            return True
            
        except Exception as e:
            logger.error(f"飞书适配器连接失败: {e}")
            return False
    
    async def disconnect(self):
        """断开连接"""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
        
        self._connected = False
        logger.info("飞书适配器已断开")
    
    async def send_message(
        self,
        chat_id: str,
        content: str,
        message_type: MessageType = MessageType.TEXT,
        files: Optional[List[Dict]] = None,
        **kwargs
    ) -> MessageResponse:
        """
        发送消息到飞书
        
        飞书支持的消息类型:
        - text: 文本消息
        - post: 富文本消息
        - image: 图片消息
        - interactive: 交互卡片
        - share_chat: 分享群聊
        - share_user: 分享用户
        """
        try:
            # 判断消息接收者类型
            if chat_id.startswith("ou_"):  # 用户ID
                receive_id_type = "user_id"
            elif chat_id.startswith("oc_"):  # 群聊ID
                receive_id_type = "chat_id"
            elif chat_id.startswith("on_"):  # 部门ID
                receive_id_type = "department_id"
            else:
                receive_id_type = "open_id"
            
            # 构建消息体
            msg_data = {
                "receive_id": chat_id,
                "msg_type": message_type.value,
                "content": self._build_message_content(content, message_type, files, kwargs),
            }
            
            if receive_id_type:
                msg_data["receive_id_type"] = receive_id_type
            
            # 发送消息
            result = await self._make_request("POST", "im/v1/messages", json=msg_data)
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
                message_id=message_id or "unknown"
            )
            
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return MessageResponse.error_response(
                platform=self.platform,
                chat_id=chat_id,
                error=str(e)
            )
    
    def _build_message_content(self, content: str, message_type: MessageType, 
                              files: Optional[List[Dict]], kwargs: Dict) -> str:
        """构建消息内容JSON字符串"""
        msg_type = message_type.value
        
        if msg_type == "text":
            # 文本消息
            message_content = {
                "text": content
            }
            
        elif msg_type == "post":
            # 富文本消息
            # 简单的富文本格式
            message_content = {
                "post": {
                    "zh_cn": {
                        "title": kwargs.get("title", "消息"),
                        "content": [
                            [{
                                "tag": "text",
                                "text": content
                            }]
                        ]
                    }
                }
            }
            
        elif msg_type == "image":
            # 图片消息
            image_key = kwargs.get("image_key")
            if image_key:
                message_content = {
                    "image_key": image_key
                }
            else:
                # 如果没有image_key，使用文本消息
                message_content = {"text": f"[图片] {content}"}
                
        elif msg_type == "interactive":
            # 交互卡片
            # 这里使用一个简单的卡片示例
            message_content = {
                "config": {
                    "wide_screen_mode": True
                },
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": kwargs.get("title", "通知")
                    }
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "plain_text",
                            "content": content
                        }
                    }
                ]
            }
            
        else:
            # 默认使用文本消息
            logger.warning(f"暂不支持的消息类型: {msg_type}，使用文本消息")
            message_content = {"text": content}
        
        return json.dumps(message_content, ensure_ascii=False)
    
    async def receive_messages(self, handler: Callable[[UnifiedMessage], None]):
        """
        接收消息（事件订阅模式）
        
        飞书使用事件订阅模式，需要配置事件订阅和Webhook服务器
        """
        # 这里应该处理飞书的事件订阅回调
        # 飞书事件需要验证和加解密
        
        async def event_handler(request):
            """事件处理器"""
            try:
                data = await request.json()
                logger.debug(f"收到飞书事件: {data}")
                
                # 验证事件（如果有verification_token）
                if "challenge" in data:
                    # 这是URL验证请求
                    return {"challenge": data["challenge"]}
                
                # 解析加密数据（如果有encrypt_key）
                if self.encrypt_key and "encrypt" in data:
                    decrypted = self._decrypt_event(data["encrypt"])
                    if decrypted:
                        data = json.loads(decrypted)
                
                # 处理事件
                event = data.get("event", {})
                event_type = data.get("type", "")
                
                if event_type == "im.message.receive_v1":
                    # 消息接收事件
                    message = self._parse_message_event(event)
                    if message:
                        await self._handle_message(message)
                
                # 返回成功响应
                return {"code": 0}
                
            except Exception as e:
                logger.error(f"处理事件异常: {e}")
                return {"code": 1, "msg": "internal error"}
        
        # 在实际部署中，这里应该启动一个Web服务器
        # 飞书事件订阅需要配置可信域名
        
        logger.info("飞书适配器使用事件订阅模式，需要配置Webhook服务器")
        
        # 注册处理器
        self.register_message_handler(handler)
    
    def _decrypt_event(self, encrypt_data: str) -> Optional[str]:
        """解密飞书事件数据"""
        try:
            if not self.encrypt_key:
                return None
            
            # Base64解码
            encrypted_bytes = base64.b64decode(encrypt_data)
            
            # 这里实现飞书的解密逻辑
            # 实际需要根据飞书文档实现完整的解密算法
            
            # 简化版本：直接返回（实际生产环境需要完整实现）
            logger.warning("飞书事件解密未完全实现，请参考官方文档")
            return encrypt_data
            
        except Exception as e:
            logger.error(f"解密飞书事件失败: {e}")
            return None
    
    def _parse_message_event(self, event: Dict) -> Optional[UnifiedMessage]:
        """解析飞书消息事件"""
        try:
            message_data = event.get("message", {})
            sender = event.get("sender", {})
            
            message_id = message_data.get("message_id", "")
            chat_id = message_data.get("chat_id", "")
            chat_type = ChatType.GROUP if chat_id.startswith("oc_") else ChatType.PRIVATE
            user_id = sender.get("sender_id", {}).get("user_id", "")
            
            # 消息内容
            content_data = json.loads(message_data.get("content", "{}"))
            msg_type = message_data.get("message_type", "text")
            
            # 提取文本内容
            text = ""
            files = []
            
            if msg_type == "text":
                text = content_data.get("text", "")
            elif msg_type == "image":
                text = "图片消息"
                image_key = content_data.get("image_key", "")
                if image_key:
                    files.append(FileInfo(
                        type="image",
                        url=f"https://open.feishu.cn/open-apis/im/v1/images/{image_key}",
                        name=image_key,
                        size=None,
                        path=None,
                        mime_type=None
                    ))
            elif msg_type == "file":
                file_key = content_data.get("file_key", "")
                text = content_data.get("file_name", "文件消息")
                if file_key:
                    files.append(FileInfo(
                        type="file",
                        name=content_data.get("file_name", ""),
                        url=f"https://open.feishu.cn/open-apis/im/v1/files/{file_key}",
                        size=None,
                        path=None,
                        mime_type=None
                    ))
            
            # 创建统一消息对象
            message = UnifiedMessage(
                platform=self.platform,
                message_id=message_id,
                chat_id=chat_id,
                user_id=user_id,
                username=sender.get("sender_id", {}).get("name", None),
                chat_type=chat_type,
                message_type=MessageType(msg_type),
                text=text,
                files=files,
                raw_data=event,
                is_reply=False,
                is_forwarded=False,
                is_edited=False,
                is_deleted=False
            )
            
            return message
            
        except Exception as e:
            logger.error(f"解析飞书消息事件失败: {e}")
            return None
    
    async def upload_file(self, file_path: str, file_type: str = "file") -> Optional[str]:
        """
        上传文件到飞书
        
        Args:
            file_path: 文件路径
            file_type: 文件类型 (image, file)
            
        Returns:
            str: file_key 或 image_key
        """
        try:
            token = await self._get_tenant_access_token()
            if not token:
                return None
            
            # 飞书文件上传API
            url = f"{self.base_url}/im/v1/files"
            headers = {
                "Authorization": f"Bearer {token}",
            }
            
            # 读取文件
            with open(file_path, "rb") as f:
                files = {"file": f}
                params = {"file_type": file_type}
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, headers=headers, params=params, files=files)
                    response.raise_for_status()
                    
                    data = response.json()
                    if data.get("code") == 0:
                        file_key = data.get("data", {}).get("file_key")
                        logger.info(f"文件上传成功: {file_path} -> {file_key}")
                        return file_key
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
        # 飞书获取用户信息API
        # 由于是同步方法，这里只返回基础信息
        return {
            "user_id": user_id,
            "platform": self.platform.value,
            "name": user_id  # 实际应该调用API获取
        }


# 注册适配器到工厂
from ..adapters.base import AdapterFactory
AdapterFactory.register(PlatformType.FEISHU, FeishuAdapter)