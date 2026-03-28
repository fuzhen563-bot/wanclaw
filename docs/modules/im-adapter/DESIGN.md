# WanClaw IM Adapter

统一消息收发服务，支持QQ、微信、企业微信、飞书、Telegram五大主流IM平台，为WanClaw AI助手提供多平台通信能力。

## 1. Overview

### Platform Support

| 平台 | 类型 | 协议 | 状态 | 优势 | 挑战 | 推荐用途 |
|------|------|------|------|------|------|----------|
| **企业微信** | 企业IM | HTTP/Webhook | ✅ 已实现 | API完善，集成办公 | 需企业认证 | 企业内部协作 |
| **飞书** | 企业IM | HTTP/Webhook | ✅ 已实现 | 功能丰富，开放API | 需企业认证 | 团队项目管理 |
| **QQ** | 社交IM | WebSocket/HTTP | ✅ 已实现 | 用户基数大，群组功能强 | API限制较多 | 社区服务支持 |
| **微信** | 社交IM | HTTP/Webhook | ✅ 已实现 | 普及率高，生态完善 | 官方API限制严格 | 个人用户服务 |
| **Telegram** | 社交IM | HTTP长轮询 | ✅ 已实现 | API友好，国际化 | 国内网络限制（需代理） | 技术社区服务 |

### Key Features

- **多平台支持**：统一接口支持5大主流IM平台
- **标准化消息格式**：统一的消息模型，简化处理逻辑
- **异步高性能**：基于asyncio实现，支持高并发消息处理
- **插件化架构**：适配器可动态注册和加载
- **完整监控**：提供健康检查和运行状态监控
- **安全可靠**：支持消息签名验证和频率限制

## 2. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    WanClaw核心服务                       │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │
│  │ 消息解析 │  │ 命令分发 │  │ 结果处理 │  │ 会话管理 │  │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  │
│       │            │            │            │       │
└───────┼────────────┼────────────┼────────────┼───────┘
        │            │            │            │
┌───────▼────────────▼────────────▼────────────▼───────┐
│                 统一IM适配器网关                      │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │
│  │ 协议转换 │  │ 认证管理 │  │ 会话映射 │  │ 错误处理 │  │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  │
│       │            │            │            │       │
└───────┼────────────┼────────────┼────────────┼───────┘
        │            │            │            │
    ┌───▼──┐    ┌───▼──┐    ┌───▼──┐    ┌───▼──┐    ┌───▼──┐
    │企业微信│    │  飞书  │    │  QQ   │    │ 微信  │    │  TG  │
    └──────┘    └──────┘    └──────┘    └──────┘    └──────┘
```

**Module Layers:**
- **消息网关层**：统一消息格式，协议转换
- **平台适配层**：各平台SDK封装，实现 `IMAdapter` 接口
- **会话管理层**：用户会话状态维护
- **认证管理层**：平台认证和权限管理

## 3. Getting Started

### 3.1 Install Dependencies

```bash
cd backend/im_adapter
pip install -r requirements.txt
```

### 3.2 Configure Platforms

```bash
cp config/example_config.yaml config/config.yaml
```

### 3.3 Start Service

```bash
# Direct run
python main.py

# Or start API service with uvicorn
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### 3.4 Test Connection

```bash
python main.py --health   # Health check
python main.py --test     # Send test message
```

## 4. Platform Configuration

### 4.1 企业微信 (WeCom)

1. 登录[企业微信管理后台](https://work.weixin.qq.com/)
2. 创建应用，获取 `corp_id`, `agent_id`, `secret`
3. 配置应用可信域名和接收消息服务器

```yaml
wecom:
  enabled: true
  corp_id: "your_corp_id"
  agent_id: "your_agent_id"
  secret: "your_secret"
```

### 4.2 飞书 (Feishu)

1. 登录[飞书开放平台](https://open.feishu.cn/)
2. 创建企业自建应用
3. 配置事件订阅，获取 `app_id`, `app_secret`, `verification_token`

```yaml
feishu:
  enabled: true
  app_id: "your_app_id"
  app_secret: "your_app_secret"
  verification_token: "your_token"
  encrypt_key: "your_key"
```

### 4.3 QQ (OneBot)

1. 部署OneBot兼容的QQ机器人（如go-cqhttp、Mirai等）
2. 配置WebSocket或HTTP服务器
3. 填写服务器地址和认证信息

```yaml
qq:
  enabled: true
  bot_id: "your_bot_id"
  bot_secret: "your_bot_secret"
  qq_number: "123456789"
  protocol: "onebot"  # onebot, mirai
```

### 4.4 微信 (WeChat)

建议使用企业微信接口。个人微信如需使用，考虑第三方框架：

```yaml
wechat:
  enabled: false  # 需要特殊配置
  type: "official"  # official, work, thirdparty
  app_id: "your_app_id"
  app_secret: "your_app_secret"
```

### 4.5 Telegram

1. 联系 [@BotFather](https://t.me/BotFather) 创建机器人
2. 获取 `bot_token`
3. 国内用户需配置代理服务器

```yaml
telegram:
  enabled: true
  bot_token: "your_bot_token"
  proxy: null  # 代理配置
```

## 5. API Reference

### 5.1 UnifiedMessage Format

```python
class UnifiedMessage:
    platform: PlatformType      # 平台标识
    message_id: str            # 消息ID
    chat_id: str               # 聊天ID
    user_id: str               # 用户ID
    username: str              # 用户名
    chat_type: ChatType        # 聊天类型（私聊/群聊）
    message_type: MessageType  # 消息类型（文本/图片/文件等）
    text: str                  # 消息文本
    files: List[FileInfo]      # 文件列表
    is_command: bool           # 是否为命令
    raw_data: Dict             # 原始平台数据
```

### 5.2 Send Message

```python
from gateway import get_gateway
from models.message import PlatformType, MessageType

gateway = get_gateway()

# 发送文本消息
response = await gateway.send_message(
    platform=PlatformType.TELEGRAM,
    chat_id="123456789",
    content="Hello from WanClaw!",
    message_type=MessageType.TEXT
)

# 发送图片消息
response = await gateway.send_message(
    platform=PlatformType.WECOM,
    chat_id="user@corp",
    content="这是一张图片",
    message_type=MessageType.IMAGE,
    files=[{"path": "/path/to/image.jpg"}]
)
```

### 5.3 Broadcast Message

```python
responses = await gateway.broadcast_message(
    platforms=[PlatformType.WECOM, PlatformType.FEISHU],
    chat_ids=["user1", "user2"],
    content="重要通知",
    message_type=MessageType.TEXT
)
```

### 5.4 Register Message Handler

```python
from models.message import UnifiedMessage

async def message_handler(message: UnifiedMessage):
    print(f"收到来自 {message.platform} 的消息: {message.text}")

    if message.is_command:
        command = message.get_command()
        args = message.get_command_args()

    if message.text == "ping":
        await gateway.send_message(
            platform=message.platform,
            chat_id=message.chat_id,
            content="pong",
            message_type=MessageType.TEXT
        )

gateway.register_message_handler(message_handler)
```

### 5.5 Health Check

```python
health = await gateway.health_check()
print(f"服务运行中: {health['running']}")
print(f"适配器数量: {health['adapter_count']}")
```

## 6. IMAdapter Interface

```python
class IMAdapter(ABC):
    """IM适配器基类，所有平台适配器必须实现此接口"""

    @abstractmethod
    async def connect(self) -> bool:
        """连接平台"""

    @abstractmethod
    async def disconnect(self):
        """断开连接"""

    @abstractmethod
    async def send_message(self, chat_id: str, content: dict, **kwargs) -> bool:
        """发送消息"""

    @abstractmethod
    async def receive_messages(self, handler: Callable) -> None:
        """接收消息（回调处理）"""

    @abstractmethod
    async def upload_file(self, file_path: str, file_type: str) -> str:
        """上传文件到平台"""

    @abstractmethod
    def get_user_info(self, user_id: str) -> dict:
        """获取用户信息"""
```

## 7. Deployment

### 7.1 Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  im-adapter:
    build: ./backend/im_adapter
    ports:
      - "8000:8000"  # API端口
      - "9090:9090"  # 监控端口
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    environment:
      - TZ=Asia/Shanghai
      - IM_CONFIG_PATH=/app/config/im_config.yaml
    restart: unless-stopped
```

### 7.2 Systemd Service

```ini
# /etc/systemd/system/wanclaw-im.service
[Unit]
Description=WanClaw IM Adapter Service
After=network.target

[Service]
Type=simple
User=wanclaw
WorkingDirectory=/opt/wanclaw/backend/im_adapter
ExecStart=/usr/bin/python main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## 8. Monitoring & Logging

### 8.1 Metrics

| Metric | Description |
|--------|-------------|
| `im_connections_total` | 连接数 |
| `im_messages_received_total` | 接收消息数 |
| `im_messages_sent_total` | 发送消息数 |
| `im_errors_total` | 错误数 |
| `im_latency_seconds` | 消息延迟 |

### 8.2 Log Format

```json
{
  "timestamp": "2026-03-22T10:30:00Z",
  "level": "INFO",
  "platform": "wecom",
  "chat_id": "chat_123",
  "user_id": "user_456",
  "message_type": "text",
  "action": "send",
  "status": "success",
  "duration_ms": 150
}
```

### 8.3 Logging Configuration

```yaml
logging:
  level: "INFO"
  file_path: "./logs/im_adapter.log"
  max_size: 10485760  # 10MB
  backup_count: 5
```

### 8.4 Debug Mode

```bash
export LOG_LEVEL=DEBUG
python main.py
```

## 9. Security

### 9.1 Authentication

- API密钥加密存储，使用环境变量或密钥管理服务
- Token自动刷新机制，认证失效自动重连
- IP白名单控制访问权限

### 9.2 Message Validation

- 启用消息签名验证，防止伪造消息
- 验证消息时间戳，防止重放攻击
- 检查消息来源可信性

### 9.3 Rate Limiting

```yaml
security:
  rate_limit: 10  # 消息频率限制（条/秒）
  file_size_limit: 50  # MB
  command_whitelist: ["help", "status", "skill"]
```

### 9.4 Access Control

- 用户黑白名单机制
- 命令权限分级控制
- 群组管理控制
- 操作审计日志记录

### 9.5 File Security

- 文件类型白名单检查
- 文件大小限制控制
- 敏感信息过滤

## 10. Performance

### 10.1 Connection Pool

```python
self.http_client = httpx.AsyncClient(
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    timeout=httpx.Timeout(30.0)
)
```

### 10.2 Message Queue

```python
import asyncio
message_queue = asyncio.Queue(maxsize=1000)

async def process_messages():
    while True:
        message = await message_queue.get()
        await handle_message(message)
```

### 10.3 Caching

```python
import cachetools

user_cache = cachetools.TTLCache(maxsize=1000, ttl=300)
token_cache = cachetools.TTLCache(maxsize=10, ttl=3600)
```

### 10.4 Fault Tolerance

- 连接断开：自动重连机制，指数退避策略
- 消息丢失：消息队列持久化，确认重发
- 认证失效：token自动刷新
- 平台限制：频率限制，批量处理优化

## 11. Development Guide

### 11.1 Add New Platform Adapter

1. 创建适配器类继承 `IMAdapter`
2. 实现核心接口方法
3. 注册到适配器工厂

```python
# adapters/new_platform.py
from .base import IMAdapter
from ..models.message import PlatformType

class NewPlatformAdapter(IMAdapter):
    def __init__(self, config: Dict):
        super().__init__(PlatformType.NEW_PLATFORM, config)

    async def connect(self) -> bool:
        pass

    async def send_message(self, chat_id: str, content: str, **kwargs):
        pass

# 注册适配器
from ..adapters.base import AdapterFactory
AdapterFactory.register(PlatformType.NEW_PLATFORM, NewPlatformAdapter)
```

### 11.2 Extend Message Types

```python
class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    VOICE = "voice"
    VIDEO = "video"
    CUSTOM = "custom"
```

## 12. Testing

### 12.1 Unit Tests

- 消息格式转换测试
- 适配器接口测试
- 错误处理测试

### 12.2 Integration Tests

- 平台连接测试
- 消息收发测试
- 多平台协同测试

### 12.3 Stress Tests

- 并发消息处理测试
- 长时间运行稳定性测试
- 故障恢复测试

## 13. Troubleshooting

| 问题 | 排查方法 |
|------|----------|
| 连接失败 | 检查网络、防火墙、配置参数，查看日志 |
| 消息发送失败 | 验证chat_id格式、用户/群组权限、平台API错误信息 |
| Webhook接收失败 | 确保公网可访问、检查URL验证、签名加密设置 |

## 14. Roadmap

- [ ] 更多平台支持（钉钉、Discord、Slack等）
- [ ] 消息持久化存储
- [ ] 消息队列和流量控制
- [ ] 高级消息模板系统
- [ ] 用户管理和权限系统
- [ ] 消息分析和报表功能
- [ ] 语音/视频消息支持
- [ ] 富文本消息和消息撤回功能
- [ ] 平台状态监控面板
- [ ] 自动化告警系统

---

**文档版本**: 2.0
**创建时间**: 2026年3月22日
**更新记录**: 合并实现指南与设计文档
