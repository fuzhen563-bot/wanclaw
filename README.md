# WanClaw（万爪） — 企业级 AI 智能助手

> 开源 AI 个人/企业助手，支持 20+ 平台、智能调度、RPA自动化、工作流编排、多租户

[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-green.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-58%20passed-brightgreen.svg)]()

---
## 核心升级（V1.0 → V2.0）

| 维度 | V1.0 | V2.0 |
|------|------|------|
| **架构** | 单机运行 | ✅ 分布式Gateway集群 + Redis |
| **AI大脑** | 基础LLM调用 | ✅ ReAct工具链规划 + 意图分类 |
| **执行层** | 无 | ✅ 桌面自动化 + 浏览器RPA + 安全沙箱 |
| **工作流** | 技能硬编码 | ✅ DAG可视化编排 + 条件分支 |
| **任务队列** | 无 | ✅ 异步任务 + 断点续传 + 重试 |
| **安全合规** | 基础认证 | ✅ RBAC + 多租户 + 审计日志 |
| **告警通知** | 无 | ✅ 钉钉/飞书/邮件/Webhook |
| **数据分析** | 无 | ✅ DAU/MAU + 营收报表 + 实时监控 |
| **API网关** | 无 | ✅ 统一入口 + API Key + 限流 |

---

## 功能特性

### 1. 多平台消息通道（20+）

| 分类 | 平台 |
|------|------|
| **即时通讯** | 企业微信、飞书、QQ、微信、Telegram、WhatsApp、Discord、Slack |
| **电商平台** | 淘宝/天猫、京东、拼多多、抖音电商、快手小店、有赞、快多通 |
| **其他** | Signal、Microsoft Teams、Matrix、LINE、IRC、钉钉 |

### 2. AI 模型引擎（6 种提供商）

| 提供商 | 模型 | 特点 |
|--------|------|------|
| Ollama | qwen2.5 / llama3 | 本地部署，零成本 |
| DeepSeek | deepseek-chat / deepseek-coder | 高性价比 |
| 通义千问 | qwen-plus / qwen-max | 中文最强 |
| 智谱 GLM | glm-4-flash / glm-4 | 免费额度 |
| Moonshot | moonshot-v1-8k/32k/128k | 长上下文 |
| OpenAI | gpt-4o-mini / gpt-4o | 通用能力 |

### 3. V2.0 新增核心能力

#### 分布式架构
```
┌─────────────────┐     ┌─────────────────┐
│   Gateway 节点1  │     │   Gateway 节点2  │
│   (店铺A)        │     │   (店铺B)        │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────────────────────────────┐
│              Redis Cluster               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐│
│  │ Pub/Sub  │ │ Streams │ │ Session  ││
│  └──────────┘ └──────────┘ └──────────┘│
└─────────────────────────────────────────┘
```

#### ReAct Agent 工具链
```
思考 → 行动 → 观察 → 反思 → ... → 最终答案
```

#### 工作流编排
```
开始 → 任务节点 → 条件分支 → [是]→ 审核 → 结束
                            [否]→ 自动处理 → 结束
```

---

## 快速开始

### 方式一：Docker 部署（推荐）

```bash
git clone https://github.com/fuzhen563-bot/wanclaw.git
cd wanclaw
docker-compose up -d
```

### 方式二：一键安装

```bash
curl -fsSL https://raw.githubusercontent.com/wanclaw/wanclaw/main/install.sh | bash
```

### 方式三：手动安装

```bash
git clone https://github.com/fuzhen563-bot/wanclaw.git
cd wanclaw
pip install -r requirements.txt
python -m wanclaw.main
```

### 安装后配置

1. 访问 `http://localhost:8000/admin`
2. 首次登录使用默认密码: `wanclaw`
3. 在 **AI 配置** 页面填入 API Key
4. 在 **IM平台** 页面配置各平台参数

---

## V2.0 项目结构

```
wanclaw/
├── wanclaw/
│   ├── backend/
│   │   ├── gateway/              # 分布式Gateway
│   │   │   └── distributed.py    # Redis Pub/Sub + Session同步
│   │   ├── tasks/               # 异步任务队列
│   │   │   └── tasks.py         # 断点续传 + 重试机制
│   │   ├── ai/
│   │   │   ├── react_agent.py   # ReAct 工具链规划
│   │   │   ├── router.py       # 多模型自动容灾
│   │   │   └── embedding.py    # 向量知识库
│   │   ├── agent/
│   │   │   ├── orchestrator.py  # 中央调度大脑
│   │   │   ├── memory.py        # 5层记忆系统
│   │   │   └── context_engine.py # 7 Hooks 上下文
│   │   ├── automation/          # 桌面自动化
│   │   │   ├── input_controller.py  # 鼠标键盘控制
│   │   │   └── sandbox.py       # 安全沙箱
│   │   ├── rpa/                # 浏览器RPA
│   │   │   └── playwright_driver.py
│   │   ├── workflows/          # 工作流引擎
│   │   │   └── engine.py       # DAG编排 + 定时任务
│   │   ├── auth/               # 安全认证
│   │   │   ├── rbac.py         # RBAC权限系统
│   │   │   └── tenant.py        # 多租户 + 套餐
│   │   ├── notification/       # 告警通知
│   │   │   └── manager.py       # 钉钉/飞书/邮件
│   │   ├── api_gateway/        # API网关
│   │   │   └── gateway.py       # 认证 + 限流
│   │   ├── analytics/          # 数据分析
│   │   │   └── analytics.py     # DAU/MAU + 营收
│   │   ├── audit/             # 操作审计
│   │   │   └── audit.py        # 全链路日志
│   │   ├── im_adapter/         # 20+平台适配器
│   │   └── skills/             # 27+ 内置技能
│   ├── main.py                 # 服务入口
│   └── examples/               # 集成示例
├── tests/
│   └── test_v2.py             # 58项功能测试
├── docker-compose.yml          # Docker部署
├── Dockerfile
└── README_V2.md
```

---

## V2.0 新增模块详解

### 中央调度大脑 (Orchestrator)

```python
from wanclaw.backend.agent import AgentOrchestrator

orchestrator = AgentOrchestrator(llm, skill_manager, memory)
result = await orchestrator.process("帮我处理今天的订单", context)
```

### ReAct Agent

```python
from wanclaw.backend.ai import ReActAgent

agent = ReActAgent(llm, tools=[skill_tool, calc_tool])
result = await agent.run("计算今天的总收入")
```

### 工作流引擎

```python
from wanclaw.backend.workflows import WorkflowEngine

engine = get_workflow_engine()
workflow = await engine.create_workflow(name="订单处理")
await engine.execute(workflow.workflow_id, {"amount": 100})
```

### 多租户 + RBAC

```python
from wanclaw.backend.auth import TenantService, AuthService

# 创建租户
tenant_svc = await get_tenant_service()
result = await tenant_svc.create_tenant_with_admin(
    tenant_name="厦门万岳",
    admin_email="admin@company.com",
    plan=PlanType.PROFESSIONAL,
)
```

### 告警通知

```python
from wanclaw.backend.notification import get_notification_manager

notifier = get_notification_manager()
await notifier.send(
    title="系统告警",
    content="CPU使用率超过90%",
    level=AlertLevel.WARNING,
)
```

### 数据分析

```python
from wanclaw.backend.analytics import get_analytics, get_revenue_analytics

analytics = await get_analytics()
dau = await analytics.get_dau()

revenue = await get_revenue_analytics()
mrr = await revenue.get_mrr()
```

---

## API 文档（70+ 端点）

### 对话引擎
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/conversation/reply` | 发送对话回复 |
| GET | `/api/conversation/context/{platform}/{chat_id}` | 获取会话上下文 |

### AI 引擎
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/admin/ai/chat` | AI 聊天 |
| POST | `/api/admin/ai/chat/stream` | 流式聊天 (SSE) |
| POST | `/api/admin/ai/react` | ReAct 执行 |

### 工作流
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/workflows` | 创建工作流 |
| GET | `/api/workflows/{id}` | 获取工作流 |
| POST | `/api/workflows/{id}/execute` | 执行工作流 |

### 多租户
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/tenants` | 创建租户 |
| GET | `/api/tenants/{id}/stores` | 获取店铺 |
| GET | `/api/tenants/{id}/agents` | 获取客服 |

### 告警通知
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/notifications/send` | 发送通知 |
| GET | `/api/notifications/configs` | 获取配置 |
| POST | `/api/notifications/rules` | 添加告警规则 |

### 数据分析
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/analytics/dau` | 日活统计 |
| GET | `/api/analytics/revenue` | 营收报表 |

---

## Docker 部署

```bash
# 启动所有服务（包括Redis）
docker-compose up -d

# 查看日志
docker-compose logs -f

# 查看服务状态
docker-compose ps

# 停止
docker-compose down
```

---

## 运行测试

```bash
# 运行所有功能测试
python tests/test_v2.py

# 运行pytest
pytest tests/ -v
```

---

## 与 OpenClaw 对比

| 维度 | OpenClaw | WanClaw V2.0 |
|------|----------|---------------|
| IM 通道 | 25+ | 20+ |
| 电商平台 | ❌ | ✅ |
| 分布式架构 | ❌ | ✅ Redis集群 |
| ReAct Agent | ❌ | ✅ |
| 工作流编排 | ❌ | ✅ DAG |
| 任务队列 | ❌ | ✅ Redis Streams |
| 桌面自动化 | ❌ | ✅ pyautogui |
| 浏览器RPA | ❌ | ✅ Playwright |
| 安全沙箱 | ❌ | ✅ AST验证 |
| RBAC权限 | ❌ | ✅ |
| 多租户 | ❌ | ✅ |
| 告警通知 | ❌ | ✅ 5渠道 |
| 数据分析 | ❌ | ✅ DAU/MAU/营收 |
| API网关 | ❌ | ✅ |
| 操作审计 | ❌ | ✅ 全链路 |
| 中文本地化 | 弱 | ✅ 完整 |

---

## 环境变量

| 变量 | 说明 | 必填 |
|------|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key | 是 |
| `WANCLAW_REDIS_URL` | Redis 连接地址 | 是 |
| `WECOM_SECRET` | 企业微信 Secret | 平台启用时 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | 平台启用时 |
| `OLLAMA_BASE_URL` | Ollama 地址 | 使用本地模型时 |

---

## 技术栈

- **后端**: Python 3.8+, FastAPI, asyncio
- **消息队列**: Redis Streams
- **任务队列**: Celery (可选)
- **RPA**: Playwright, PyAutoGUI
- **向量搜索**: Ollama Embeddings
- **部署**: Docker, Docker Compose, systemd

---

## License

MIT License — 可商用，可修改，可分发

---

## 借鉴文档

本项目在开发过程中参考了以下开源项目与文档（按参考程度排序）：

| 项目/文档 | 参考内容 | 来源 |
|-----------|----------|------|
| **OpenClaw** (PSPDFKit创始人 Peter Steinberger) | 整体架构设计、Channel Adapter 模式、Gateway 控制平面、SKILL.md 格式、ContextEngine 7 Hooks、Per-Account SOUL、Secrets 64-Surface、QMD、DAG Store、Swarm Memory | https://github.com/openclaw/openclaw |
| **OpenClaw 官方文档** (openclawlab.com) | 配置示例、多平台部署、Gateway API、Session Scope、DM Policy 模型 | https://openclawlab.com |
| **SoulClaw Fork** | SoulScan 规则集（58+）、Persona Drift 检测、Swarm Memory SQLite 实现、DAG Store 拓扑排序 | OpenClaw 社区 |
| **lossless-claw** (DAG上下文) | LosslessContextEngine 实现思路、SQLite DAG 消息存储、后台 Gemini Flash-Lite 压缩 | OpenClaw 社区讨论 |
| **Tobi Lütze — QMD** | Query Markdown Documents 语义工作区搜索概念 | OpenClaw 架构讨论 |
| **FastAPI** | Web 框架架构、端点设计、FileResponse 静态服务 | https://fastapi.tiangolo.com |
| **Tailwind CSS** | 前端样式系统、iOS 风格设计令牌 | https://tailwindcss.com |
| **Lucide Icons** | 前端图标库 | https://lucide.dev |

---

**版权所有 © 2026 厦门亦梓科技有限公司**  
**Copyright © 2026 Xiamen Yizi Technology Co., Ltd. All Rights Reserved.**

**版权所有 © 2026 厦门万跃科技有限公司**  
**Copyright © 2026 Xiamen Wanyue Technology Co., Ltd. All Rights Reserved.**

---

> **声明**：WanClaw V2.0 是基于 OpenClaw 架构思路开发的独立项目，兼容 OpenClaw 技能格式，并非 OpenClaw 的分支或衍生版本。代码实现为全新编写。
