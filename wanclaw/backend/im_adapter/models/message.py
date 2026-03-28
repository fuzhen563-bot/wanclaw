"""
统一消息模型定义
支持多平台消息格式标准化
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """消息类型枚举"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    VOICE = "voice"
    VIDEO = "video"
    LOCATION = "location"
    STICKER = "sticker"
    LINK = "link"
    COMMAND = "command"
    SYSTEM = "system"


class ChatType(str, Enum):
    """聊天类型枚举"""
    PRIVATE = "private"
    GROUP = "group"
    CHANNEL = "channel"
    SUPERGROUP = "supergroup"


class PlatformType(str, Enum):
    """平台类型枚举"""
    WECOM = "wecom"
    FEISHU = "feishu"
    QQ = "qq"
    WECHAT = "wechat"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    DISCORD = "discord"
    SLACK = "slack"
    SIGNAL = "signal"
    TEAMS = "teams"
    MATRIX = "matrix"
    LINE = "line"
    IRC = "irc"
    TAOBAO = "taobao"
    JD = "jd"
    PINDUODUO = "pinduoduo"
    DOUYIN = "douyin"
    KUAISHOU = "kuaishou"
    YOUZAN = "youzan"
    KOUDATONG = "koudatong"


class FileInfo(BaseModel):
    """文件信息模型"""
    type: str = Field(..., description="文件类型: image, file, voice, video")
    url: Optional[str] = Field(None, description="文件URL")
    path: Optional[str] = Field(None, description="文件本地路径")
    name: Optional[str] = Field(None, description="文件名")
    size: Optional[int] = Field(None, description="文件大小(字节)")
    mime_type: Optional[str] = Field(None, description="MIME类型")


class MentionInfo(BaseModel):
    """提及用户信息"""
    user_id: str = Field(..., description="用户ID")
    username: Optional[str] = Field(None, description="用户名")
    display_name: Optional[str] = Field(None, description="显示名称")


class UnifiedMessage(BaseModel):
    """
    统一消息模型
    标准化所有平台的消息格式
    """
    # 基础信息
    platform: PlatformType = Field(..., description="平台标识")
    message_id: str = Field(..., description="平台消息ID")
    chat_id: str = Field(..., description="会话ID")
    user_id: str = Field(..., description="发送用户ID")
    
    # 元数据
    username: Optional[str] = Field(None, description="用户名/昵称")
    chat_type: ChatType = Field(ChatType.PRIVATE, description="聊天类型")
    message_type: MessageType = Field(MessageType.TEXT, description="消息类型")
    timestamp: datetime = Field(default_factory=datetime.now, description="消息时间")
    
    # 内容部分
    text: Optional[str] = Field(None, description="文本消息内容")
    files: List[FileInfo] = Field(default_factory=list, description="文件列表")
    mentions: List[MentionInfo] = Field(default_factory=list, description="提及用户列表")
    
    # 扩展数据
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="原始平台数据")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")
    
    # 状态标记
    is_reply: bool = Field(False, description="是否为回复消息")
    is_forwarded: bool = Field(False, description="是否为转发消息")
    is_edited: bool = Field(False, description="是否为编辑消息")
    is_deleted: bool = Field(False, description="是否已删除")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @property
    def is_group(self) -> bool:
        """是否为群聊消息"""
        return self.chat_type in [ChatType.GROUP, ChatType.CHANNEL, ChatType.SUPERGROUP]
    
    @property
    def is_command(self) -> bool:
        """是否为命令消息"""
        if self.message_type == MessageType.COMMAND:
            return True
        
        text = self.text
        if not text:
            return False
            
        return text.startswith('/')
    
    def get_command(self) -> Optional[str]:
        """获取命令名称"""
        if self.is_command and self.text:
            # 去除斜杠和参数
            cmd = self.text.split()[0][1:] if self.text.startswith('/') else None
            return cmd.lower() if cmd else None
        return None
    
    def get_command_args(self) -> List[str]:
        """获取命令参数"""
        if self.is_command and self.text:
            parts = self.text.split()
            return parts[1:] if len(parts) > 1 else []
        return []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "platform": self.platform,
            "message_id": self.message_id,
            "chat_id": self.chat_id,
            "user_id": self.user_id,
            "username": self.username,
            "chat_type": self.chat_type,
            "message_type": self.message_type,
            "timestamp": self.timestamp.isoformat(),
            "text": self.text,
            "files": [file.dict() for file in self.files],
            "mentions": [mention.dict() for mention in self.mentions],
            "is_group": self.is_group,
            "is_command": self.is_command
        }


class MessageResponse(BaseModel):
    """消息响应模型"""
    success: bool = Field(..., description="是否成功")
    message_id: Optional[str] = Field(None, description="发送的消息ID")
    platform: Optional[PlatformType] = Field(None, description="平台标识")
    chat_id: Optional[str] = Field(None, description="会话ID")
    error: Optional[str] = Field(None, description="错误信息")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")
    
    @classmethod
    def success_response(cls, platform: PlatformType, chat_id: str, message_id: str) -> "MessageResponse":
        """创建成功响应"""
        return cls(
            success=True,
            platform=platform,
            chat_id=chat_id,
            message_id=message_id,
            error=None
        )
    
    @classmethod
    def error_response(cls, platform: PlatformType, chat_id: str, error: str) -> "MessageResponse":
        """创建错误响应"""
        return cls(
            success=False,
            platform=platform,
            chat_id=chat_id,
            message_id=None,
            error=error
        )