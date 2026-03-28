# WanClaw IM适配器

支持QQ、微信、企业微信、飞书、Telegram的统一消息收发服务，为WanClaw AI助手提供多平台通信能力。

## 特性

- **多平台支持**：统一接口支持5大主流IM平台
- **标准化消息格式**：统一的消息模型，简化处理逻辑
- **异步高性能**：基于asyncio实现，支持高并发消息处理
- **插件化架构**：适配器可动态注册和加载
- **完整监控**：提供健康检查和运行状态监控
- **安全可靠**：支持消息签名验证和频率限制

## 支持平台

| 平台 | 类型 | 协议 | 状态 | 备注 |
|------|------|------|------|------|
| 企业微信 | 企业IM | HTTP/Webhook | ✅ 已实现 | 需要企业认证 |
| 飞书 | 企业IM | HTTP/Webhook | ✅ 已实现 | 需要应用配置 |
| QQ | 社交IM | WebSocket/HTTP | ✅ 已实现 | 基于OneBot协议 |
| 微信 | 社交IM | HTTP/Webhook | ✅ 已实现 | 支持企业微信接口 |
| Telegram | 社交IM | HTTP长轮询 | ✅ 已实现 | 需要代理（国内） |

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    WanClaw核心服务                       │
│                    (消息处理逻辑)                         │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│                    统一IM网关                            │
│           (消息路由、协议转换、状态管理)                   │
└───────┬───────┬───────┬───────┬───────┬─────────────────┘
        │       │       │       │       │
    ┌───▼──┐┌───▼──┐┌───▼──┐┌───▼──┐┌───▼──┐
    │企业微信││  飞书  ││  QQ   ││  微信  ││Telegram│
    └──────┘└──────┘└──────┘└──────┘└──────┘
```

## 快速开始

### 1. 安装依赖

```bash
cd backend/im_adapter
pip install -r requirements.txt
```

### 2. 配置平台

复制示例配置文件并修改：

```bash
cp config/example_config.yaml config/config.yaml
```

编辑 `config/config.yaml`，配置需要使用的平台：

```yaml
# 示例：启用Telegram和企业微信
telegram:
  enabled: true
  bot_token: "your_bot_token"

wecom:
  enabled: true
  corp_id: "your_corp_id"
  agent_id: "your_agent_id"
  secret: "your_secret"
```

### 3. 启动服务

```bash
# 直接运行
python main.py

# 或使用uvicorn启动API服务
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 测试连接

```bash
# 健康检查
python main.py --health

# 发送测试消息
python main.py --test
```

## API接口

IM适配器提供以下核心API：

### 发送消息

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

### 广播消息

```python
# 向多个平台广播消息
responses = await gateway.broadcast_message(
    platforms=[PlatformType.WECOM, PlatformType.FEISHU],
    chat_ids=["user1", "user2"],
    content="重要通知",
    message_type=MessageType.TEXT
)
```

### 健康检查

```python
# 获取服务状态
health = await gateway.health_check()
print(f"服务运行中: {health['running']}")
print(f"适配器数量: {health['adapter_count']}")
```

## 消息处理

### 注册消息处理器

```python
from models.message import UnifiedMessage

async def message_handler(message: UnifiedMessage):
    """自定义消息处理器"""
    print(f"收到来自 {message.platform} 的消息: {message.text}")
    
    # 处理命令
    if message.is_command:
        command = message.get_command()
        args = message.get_command_args()
        print(f"命令: {command}, 参数: {args}")
    
    # 回复消息
    if message.text == "ping":
        await gateway.send_message(
            platform=message.platform,
            chat_id=message.chat_id,
            content="pong",
            message_type=MessageType.TEXT
        )

# 注册处理器
gateway.register_message_handler(message_handler)
```

### 消息格式

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

## 平台配置指南

### 企业微信配置

1. 登录[企业微信管理后台](https://work.weixin.qq.com/)
2. 创建应用，获取 `corp_id`, `agent_id`, `secret`
3. 配置应用可信域名和接收消息服务器
4. 在配置文件中填写相应参数

### 飞书配置

1. 登录[飞书开放平台](https://open.feishu.cn/)
2. 创建企业自建应用
3. 配置事件订阅，获取 `app_id`, `app_secret`, `verification_token`
4. 在配置文件中填写相应参数

### QQ配置

1. 部署OneBot兼容的QQ机器人（如go-cqhttp、Mirai等）
2. 配置WebSocket或HTTP服务器
3. 在配置文件中填写服务器地址和认证信息

### Telegram配置

1. 联系[@BotFather](https://t.me/BotFather)创建机器人
2. 获取 `bot_token`
3. （国内用户）配置代理服务器
4. 在配置文件中填写相应参数

### 微信配置

建议使用企业微信接口，如必须使用个人微信，可考虑：
1. 使用第三方微信机器人框架（如itchat、wxpy）
2. 配置回调服务器
3. 在配置文件中选择 `thirdparty` 类型

## 部署方案

### Docker部署

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
    restart: unless-stopped
```

### 系统服务部署

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

## 监控和日志

### 监控指标

- `im_connections_total` - 连接数
- `im_messages_received_total` - 接收消息数
- `im_messages_sent_total` - 发送消息数
- `im_errors_total` - 错误数
- `im_latency_seconds` - 消息延迟

### 日志配置

```yaml
logging:
  level: "INFO"
  file_path: "./logs/im_adapter.log"
  max_size: 10485760  # 10MB
  backup_count: 5
```

## 故障排除

### 常见问题

1. **连接失败**
   - 检查网络连接和防火墙设置
   - 验证平台配置参数是否正确
   - 查看日志文件获取详细错误信息

2. **消息发送失败**
   - 检查聊天ID格式是否正确
   - 验证用户/群组权限
   - 查看平台API返回的错误信息

3. **Webhook接收失败**
   - 确保服务器公网可访问
   - 检查URL验证配置
   - 验证消息签名和加密设置

### 调试模式

```bash
# 设置调试日志级别
export LOG_LEVEL=DEBUG
python main.py

# 或修改配置文件
logging:
  level: "DEBUG"
```

## 开发指南

### 添加新平台适配器

1. 创建适配器类继承 `IMAdapter`
2. 实现核心接口方法
3. 注册到适配器工厂
4. 添加平台配置支持

```python
# adapters/new_platform.py
from .base import IMAdapter
from ..models.message import PlatformType

class NewPlatformAdapter(IMAdapter):
    def __init__(self, config: Dict):
        super().__init__(PlatformType.NEW_PLATFORM, config)
    
    async def connect(self) -> bool:
        # 实现连接逻辑
        pass
    
    async def send_message(self, chat_id: str, content: str, **kwargs):
        # 实现发送消息逻辑
        pass

# 注册适配器
from ..adapters.base import AdapterFactory
AdapterFactory.register(PlatformType.NEW_PLATFORM, NewPlatformAdapter)
```

### 扩展消息类型

在 `models/message.py` 中添加新的消息类型：

```python
class MessageType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    VOICE = "voice"
    VIDEO = "video"
    # 添加新的消息类型
    CUSTOM = "custom"
```

## 性能优化

### 连接池管理

```python
# 复用HTTP客户端连接
self.http_client = httpx.AsyncClient(
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    timeout=httpx.Timeout(30.0)
)
```

### 消息队列

```python
# 使用异步队列处理高并发消息
import asyncio
message_queue = asyncio.Queue(maxsize=1000)

async def process_messages():
    while True:
        message = await message_queue.get()
        # 处理消息
        await handle_message(message)
```

### 缓存优化

```python
# 缓存用户信息和token
import cachetools

user_cache = cachetools.TTLCache(maxsize=1000, ttl=300)
token_cache = cachetools.TTLCache(maxsize=10, ttl=3600)
```

## 安全建议

1. **API密钥安全**
   - 使用环境变量存储敏感信息
   - 定期轮换密钥
   - 限制IP访问权限

2. **消息验证**
   - 启用消息签名验证
   - 验证消息时间戳防止重放攻击
   - 检查消息来源可信性

3. **访问控制**
   - 实现用户黑白名单
   - 限制命令执行权限
   - 记录操作审计日志

## 后续开发计划

- [ ] 更多平台支持（钉钉、Discord、Slack等）
- [ ] 消息持久化存储
- [ ] 消息队列和流量控制
- [ ] 高级消息模板系统
- [ ] 用户管理和权限系统
- [ ] 消息分析和报表功能

## 许可证

MIT License