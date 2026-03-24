# WanClaw — 开源 AI 个人助手

> 对标 OpenClaw，多平台 IM 智能助手，支持 20+ 通道、上下文引擎、27+ 技能、热插拔插件

[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-green.svg)](https://python.org)

---

**版权所有 © 2025-2026 厦门万岳科技有限公司**  
**Copyright © 2025-2026 Xiamen Wanyue Technology Co., Ltd. All Rights Reserved.**

---

## 官网

- **首页**: `http://your-server:8000/`
- **管理后台**: `http://your-server:8000/admin` (默认密码: `wanclaw`)
- **API 文档**: `http://your-server:8000/docs`

---

## 功能特性

### 多平台消息通道（20+）

| 分类 | 平台 |
|------|------|
| **即时通讯** | 企业微信、飞书、QQ、微信、Telegram、WhatsApp、Discord、Slack |
| **电商平台** | 淘宝/天猫、京东、拼多多、抖音电商、快手小店、有赞、快多通 |
| **其他** | Signal、Microsoft Teams、Matrix、LINE、IRC、钉钉 |

### AI 模型引擎（6 种提供商）

| 提供商 | 模型 | 特点 |
|--------|------|------|
| Ollama | qwen2.5 / llama3 | 本地部署，零成本 |
| DeepSeek | deepseek-chat / deepseek-coder | 高性价比 |
| 通义千问 | qwen-plus / qwen-max | 中文最强 |
| 智谱 GLM | glm-4-flash / glm-4 | 免费额度 |
| Moonshot | moonshot-v1-8k/32k/128k | 长上下文 |
| OpenAI | gpt-4o-mini / gpt-4o | 通用能力 |

### 核心架构

```
微信/企业微信/淘宝/京东/Telegram/Discord/...
                    ↓
         ┌──────────────────────┐
         │   WanClaw Gateway    │
         │   (FastAPI + WS)     │
         │   端口: 8000        │
         └──────────┬───────────┘
                    ↓
┌─────────────┬──────────────┬──────────────┐
│  SOUL 记忆  │  ContextEngine │  Skill Loader │
│  (Per-Account) │  (7 Hooks)   │  (27+ Skills) │
└─────────────┴──────────────┴──────────────┘
                    ↓
         ┌──────────────────────┐
         │   Model Router      │
         │   (自动容灾切换)     │
         └──────────────────────┘
```

### 上下文引擎（ContextEngine 7 Hooks）

| Hook | 说明 |
|------|------|
| `bootstrap` | 会话启动时注入记忆上下文 |
| `ingest` | 消息入库，语义索引 |
| `assemble` | 组装 prompt 消息列表 |
| `compact` | Token 预算压缩 |
| `afterTurn` | 回合结束后的处理 |
| `prepareSubagentSpawn` | 子 Agent 启动准备 |
| `onSubagentEnded` | 子 Agent 结束回调 |

### 安全体系

- Prompt 注入检测（58+ 规则，SoulScan）
- 高危命令拦截（rm -rf、格式化等）
- 敏感信息脱敏
- 速率限制（登录 60 次/分钟）
- 认证默认启用

### 27+ 内置技能

| 分类 | 数量 | 示例 |
|------|------|------|
| 办公 | 8 | PDF 处理、Excel 合并、合同提取 |
| 运维 | 6 | 日志清理、进程监控、备份管理 |
| 营销 | 4 | 竞品监控、媒体处理、微信群监控 |
| 管理 | 4 | 会议纪要、库存管理、订单同步 |
| AI | 4 | 工作流链、NLP 任务生成 |
| 安全 | 1 | 安全扫描 |

---

## 快速开始

### 方式一：一键安装（推荐）

```bash
curl -fsSL https://raw.githubusercontent.com/wanclaw/wanclaw/main/install.sh | bash
```

### 方式二：手动安装

```bash
git clone https://github.com/wanclaw/wanclaw.git
cd wanclaw
chmod +x install.sh
./install.sh
```

### 方式三：Docker 部署

```bash
git clone https://github.com/wanclaw/wanclaw.git
cd wanclaw/dist
docker-compose up -d
```

### 安装后配置

1. 访问 `http://localhost:8000/admin`
2. 首次登录使用默认密码: `wanclaw`
3. 在 **AI 配置** 页面填入 API Key
4. 在 **IM平台** 页面配置各平台参数
5. 启动各平台适配器

---

## 脚本工具

| 脚本 | 用途 |
|------|------|
| `install.sh` | 一键安装（环境检查、依赖、systemd） |
| `wanclaw-start.sh` | 启动服务 |
| `wanclaw-stop.sh` | 停止服务 |
| `wanclaw-status.sh` | 查看运行状态 |
| `wanclaw-healthcheck.sh` | 健康检查（可配 cron） |
| `wanclaw-logs.sh` | 查看日志 |
| `uninstall.sh` | 卸载 WanClaw |

### systemd 管理

安装后自动注册 systemd 服务：

```bash
systemctl start wanclaw       # 启动
systemctl stop wanclaw        # 停止
systemctl restart wanclaw     # 重启
systemctl status wanclaw      # 状态
systemctl enable wanclaw      # 开机自启
systemctl disable wanclaw      # 关闭自启
journalctl -u wanclaw -f      # 实时日志
```

### 健康检查（配 cron）

```bash
# 每分钟检查一次
*/1 * * * * /root/wanclaw/wanclaw-healthcheck.sh >> /var/log/wanclaw-health.log 2>&1

# 异常时自动重启
*/5 * * * * /root/wanclaw/wanclaw-healthcheck.sh --auto-restart >> /var/log/wanclaw-health.log 2>&1
```

---

## 项目结构

```
wanclaw/
├── wanclaw/
│   ├── backend/
│   │   ├── im_adapter/
│   │   │   ├── api.py              # FastAPI 入口 (49 端点)
│   │   │   ├── adapters/          # 20 个 IM 平台适配器
│   │   │   ├── conversation.py    # 对话引擎
│   │   │   └── config/            # 配置文件
│   │   ├── agent/
│   │   │   ├── core.py           # Agent 自主决策循环
│   │   │   ├── memory.py         # 记忆系统 (Per-Account SOUL)
│   │   │   ├── context_engine.py  # ContextEngine (7 Hooks)
│   │   │   ├── hooks.py          # 插件 Hook 系统
│   │   │   ├── plugins.py         # 插件热加载
│   │   │   ├── soulscan.py       # Prompt 注入检测
│   │   │   ├── swarm.py          # Swarm Memory + DAG Store
│   │   │   ├── agents.py         # AGENTS.md 配置
│   │   │   ├── secrets.py         # Secrets Manager (60+ Surface)
│   │   │   ├── lossless_engine.py # Lossless 上下文 + QMD
│   │   │   └── embedding.py      # 语义搜索
│   │   ├── ai/
│   │   │   ├── ollama_client.py   # 统一 LLM 客户端
│   │   │   ├── router.py         # Model Router (自动容灾)
│   │   │   ├── auto_reply.py     # 智能客服
│   │   │   ├── nl_task.py        # 自然语言任务
│   │   │   └── voice.py          # TTS / STT
│   │   ├── skills/               # 27 个内置技能
│   │   └── frontend/
│   │       ├── index.html        # 首页/落地页
│   │       ├── admin.html         # 管理后台 (iOS 风格 SPA)
│   │       └── static/           # 静态资源
│   └── frontend/
│       ├── index.html            # 首页
│       └── static/
├── scripts/
│   ├── wanclaw-start.sh
│   ├── wanclaw-stop.sh
│   ├── wanclaw-status.sh
│   ├── wanclaw-healthcheck.sh
│   ├── wanclaw-logs.sh
│   └── uninstall.sh
├── wanclaw.service              # systemd 服务文件
├── install.sh                   # 安装脚本
└── README.md
```

---

## API 文档（49 端点）

### 对话引擎
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/conversation/reply` | 发送对话回复 |
| GET | `/api/conversation/context/{platform}/{chat_id}` | 获取会话上下文 |
| GET | `/api/conversation/rules` | 获取自动回复规则 |
| POST | `/api/conversation/rules` | 添加自动回复规则 |
| DELETE | `/api/conversation/rules/{index}` | 删除规则 |
| GET | `/api/conversation/stats` | 对话统计 |

### AI 引擎
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/admin/ai/status` | AI 状态和配置 |
| POST | `/api/admin/ai/provider` | 切换 AI 提供商 |
| POST | `/api/admin/ai/ollama/switch-model` | 切换 Ollama 模型 |
| POST | `/api/admin/ai/auto-reply/rules` | 添加自动回复规则 |
| DELETE | `/api/admin/ai/auto-reply/rules/{index}` | 删除规则 |
| POST | `/api/admin/ai/chat` | AI 聊天测试 |
| POST | `/api/admin/ai/nl-task` | 自然语言任务 |

### 管理后台
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/admin/login` | 管理员登录 |
| POST | `/api/admin/logout` | 登出 |
| POST | `/api/admin/password` | 修改密码 |
| GET | `/api/admin/config` | 获取配置 |
| PUT | `/api/admin/config` | 更新配置 |
| GET | `/api/admin/skills` | 获取技能列表 |
| POST | `/api/admin/skills/execute` | 执行技能 |
| GET | `/api/admin/logs` | 查看日志 |
| GET | `/api/admin/system` | 系统信息 |

### 插件管理
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/plugins` | 插件列表 |
| POST | `/api/plugins/{name}/load` | 加载插件 |
| POST | `/api/plugins/{name}/unload` | 卸载插件 |
| POST | `/api/plugins/{name}/reload` | 热重载插件 |
| POST | `/api/plugins/{name}/enable` | 启用插件 |
| POST | `/api/plugins/{name}/disable` | 禁用插件 |
| GET | `/api/plugins/stats` | 插件统计 |

### 技能市场
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/clawhub/skills` | 搜索技能 |
| GET | `/api/clawhub/skills/{name}` | 技能详情 |
| GET | `/api/clawhub/stats` | 市场统计 |

### 语音
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/voice/tts` | 文字转语音 |
| POST | `/api/voice/stt` | 语音转文字 |

---

## 与 OpenClaw 对比

| 维度 | OpenClaw | WanClaw |
|------|----------|---------|
| IM 通道 | 25+ | 20+ |
| 电商平台 | ❌ | ✅ 淘宝/京东/拼多多/抖音 |
| ContextEngine | 7 Hooks | ✅ 7 Hooks |
| Per-Account SOUL | ✅ | ✅ |
| Model Router | ❌ | ✅ 自动容灾 |
| Semantic Memory | ❌ | ✅ Ollama embeddings |
| SoulScan | ❌ | ✅ 58+ 规则 |
| Swarm Memory | ❌ | ✅ SQLite DAG |
| Secrets Manager | ❌ | ✅ 60+ Surface |
| Lossless Context | ❌ | ✅ DAG + QMD |
| 插件热加载 | ❌ | ✅ 5秒轮询 |
| 默认密码 | 无 | ✅ wanclaw |
| 中文本地化 | 弱 | ✅ 完整 |

---

## 平台部署文档

详细的跨平台部署指南请参考:

- [多平台部署文档](./DEPLOYMENT_MULTI_PLATFORM.md)
- [Docker 部署](./dist/docker-compose.yml)
- [构建生产版本](./build_production.sh)

### 支持的平台

- **Linux** (Ubuntu 20.04+, CentOS 8+, Debian 11+)
- **macOS** (Intel + Apple Silicon)
- **Windows** (WSL2 推荐)
- **Docker** (Linux 容器)
- **云服务器** (阿里云、腾讯云、AWS、Azure)

---

## 配置示例

`~/.wanclaw/config.yaml`:

```yaml
gateway:
  port: 8000
  auth_enabled: true
  host: 0.0.0.0

ai:
  engine: deepseek
  deepseek:
    api_key: ${DEEPSEEK_API_KEY}
    model: deepseek-chat

platforms:
  wecom:
    enabled: true
    corp_id: your_corp_id
    agent_id: 1000001
    secret: ${WECOM_SECRET}
  telegram:
    enabled: true
    bot_token: ${TELEGRAM_BOT_TOKEN}
  feishu:
    enabled: true
    app_id: cli_xxx
    app_secret: ${FEISHU_SECRET}
```

---

## 环境变量

| 变量 | 说明 | 必填 |
|------|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key | 是 |
| `WECOM_SECRET` | 企业微信 Secret | 平台启用时 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | 平台启用时 |
| `FEISHU_SECRET` | 飞书 App Secret | 平台启用时 |
| `OLLAMA_BASE_URL` | Ollama 地址 | 使用本地模型时 |
| `SECRET_KEY` | 会话加密密钥 | 推荐 |

---

## License

MIT License — 可商用，可修改，可分发

---

**版权所有 © 2025-2026 厦门万岳科技有限公司**  
**Copyright © 2025-2026 Xiamen Wanyue Technology Co., Ltd. All Rights Reserved.**

本项目基于 OpenClaw 架构思路开发，兼容 OpenClaw 技能格式。  
WanClaw is developed based on OpenClaw's architectural concepts and is compatible with OpenClaw skill formats.

---

## 借鉴文档

本项目在开发过程中参考了以下开源项目与文档（按参考程度排序）：

| 项目/文档 | 参考内容 | 来源 |
|-----------|----------|------|
| **OpenClaw** (PSPDFKit创始人 Peter Steinberger) | 整体架构设计、Channel Adapter 模式、Gateway 控制平面、SKILL.md 格式、ContextEngine 7 Hooks、Per-Account SOUL、Secrets 64-Surface、QMD、DAG Store、Swarm Memory | https://github.com/openclaw/openclaw |
| **OpenClaw 官方文档** (openclawlab.com) | 配置示例、多平台部署、Gateway API、Session Scope、DM Policy 模型 | https://openclawlab.com |
| **SoulClaw Fork** | SoulScan 规则集（58+）、Persona Drift 检测、Swarm Memory SQLite 实现、DAG Store 拓扑排序 | https://github.com/openclaw/SoulClaw |
| **lossless-claw** (DAG上下文) | LosslessContextEngine 实现思路、SQLite DAG 消息存储、后台 Gemini Flash-Lite 压缩 | OpenClaw 社区讨论 |
| **Tobi Lütze — QMD** | Query Markdown Documents 语义工作区搜索概念 | OpenClaw 架构讨论 |
| **FastAPI** | Web 框架架构、端点设计、FileResponse 静态服务 | https://fastapi.tiangolo.com |
| **Tailwind CSS** | 前端样式系统、iOS 风格设计令牌 | https://tailwindcss.com |
| **Lucide Icons** | 前端图标库 | https://lucide.dev |

> **声明**：WanClaw 是基于 OpenClaw 架构思路开发的独立项目，兼容 OpenClaw 技能格式，并非 OpenClaw 的分支或衍生版本。代码实现为全新编写。

---
