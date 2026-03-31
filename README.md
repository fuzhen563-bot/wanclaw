# WanClaw（万爪）V2.2 — 企业级 AI 智能助手管理平台

> 开源 SaaS 管理平台，支持多平台 IM 智能客服、RPA 自动化、DAG 工作流编排、RBAC 多租户、API 网关、数据分析与告警

[![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org)
[![Vue 3](https://img.shields.io/badge/Vue-3.4-blue.svg)](https://vuejs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com)

使用教程：[详细使用教程](https://chans-organization-9.gitbook.io/yizikeji)

---

**版权所有 © 2025-2026 厦门亦梓科技有限公司 / 厦门万跃科技有限公司**  
**Copyright © 2025-2026 Xiamen Yizi Technology Co., Ltd. / Xiamen Wanyue Technology Co., Ltd. All Rights Reserved.**

---

## 目录

- [特性概览](#特性概览)
- [快速开始](#快速开始)
- [架构说明](#架构说明)
- [目录结构](#目录结构)
- [完整安装](#完整安装)
- [配置指南](#配置指南)
- [API 参考](#api-参考)
- [前端开发](#前端开发)
- [插件开发](#插件开发)
- [常见问题](#常见问题)

---

## 特性概览

| 模块 | 功能 |
|------|------|
| **IM 适配层** | 企业微信 / 飞书 / 钉钉 / Telegram / WhatsApp，统一消息模型 |
| **AI 引擎** | DeepSeek / Qwen / 智谱 GLM4 / Moonshot / Ollama 多模型路由，自动容灾切换 |
| **对话引擎** | 自动回复规则、自然语言任务解析、NL → 结构化命令转换 |
| **工作流** | DAG 可视化编排（START → TASK → CONDITION → PARALLEL → END），变量替换、并行执行 |
| **RPA 自动化** | 浏览器导航、页面请求、截图，支持扩展 Playwright 浏览器自动化 |
| **技能市场** | 本地技能注册 + ClawHub 远程技能同步，统一技能执行协议 |
| **插件市场** | 插件上传、安装、启用/禁用、热加载/卸载 |
| **API 网关** | API Key 管理、权限粒度控制、限流、路由配置 |
| **数据分析** | DAU 统计、营收漏斗、转化分析、实时 QPS 监控 |
| **告警中心** | 多渠道推送（钉钉/飞书/邮件/Webhook）、规则引擎、告警历史 |
| **容灾中心** | 系统健康监控、模型容灾状态、备份管理、告警规则配置 |
| **审计日志** | 全链路操作审计、用户行为追踪、GDPR 合规报表 |
| **多租户** | 租户/套餐/店铺管理、Redis 数据隔离、RBAC 权限体系 |

---

## 快速开始

### 环境要求

- Python 3.10+
- Redis 7+
- Node.js 18+
- npm 或 yarn
- Docker（可选，用于部署）

### Docker 一键启动（推荐）

```bash
# 克隆项目
git clone https://github.com/your-org/wanclaw.git
cd wanclaw

# 启动所有服务
docker-compose up -d

# 访问管理后台
open http://localhost:40710
```

### 本地开发启动

```bash
# 1. 安装后端依赖
cd wanclaw/wanclaw/backend/im_adapter
pip install -r requirements.txt
pip install psutil openpyxl aiofiles redis fastapi uvicorn

# 2. 启动后端（端口 40710）
cd wanclaw/wanclaw
python -m wanclaw.backend.main

# 3. 另起终端，构建并启动前端
cd wanclaw/frontend-vue
npm install
npm run dev        # 开发模式 http://localhost:5173
# 或
npm run build      # 生产构建
```

### 首次登录

访问 `http://localhost:40710`，默认账号密码：

```
用户名: admin
密码: wanclaw
```

---

## 架构说明

```
                           ┌─────────────────────────────────┐
                           │         Nginx (反向代理)          │
                           │    HTTPS → 40710 (API + 前端)    │
                           └──────────────┬──────────────────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
         ┌──────────▼──────────┐  ┌───────▼────────┐  ┌────────▼────────┐
         │  Vue 3 前端 (dist/)  │  │  FastAPI 后端  │  │  IM Adapter    │
         │  Pinia + Tailwind  │  │   端口 40710    │  │  独立服务       │
         │  iOS 26 设计语言   │  │   60+ REST API  │  │  WebSocket     │
         └────────────────────┘  └────────────────┘  └────────────────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
             ┌──────▼──────┐     ┌────────▼──────┐    ┌───────▼────────┐
             │    Redis     │     │   SQLite DB   │    │   外部 API     │
             │  会话/队列   │     │   (webhook_   │    │ DeepSeek/      │
             │  指标数据    │     │   logs 等)    │    │ 钉钉/飞书等    │
             └──────────────┘     └──────────────┘    └────────────────┘
```

---

## 目录结构

```
wanclaw/
├── wanclaw/                          # Python 后端源码
│   ├── backend/
│   │   ├── main.py                   # FastAPI 主入口（端口 40710）
│   │   ├── db.py                     # SQLite 数据库（表: users, api_keys, webhook_logs 等）
│   │   ├── auth/                     # 认证授权
│   │   │   ├── rbac.py              # RBAC 权限系统（40+ 权限项）
│   │   │   └── tenant.py            # 多租户 + 套餐管理
│   │   ├── agent/                   # Agent 编排（插件加载、记忆、编排）
│   │   ├── ai/                      # AI 能力（模型路由、自动回复、NL 任务）
│   │   ├── automation/              # 桌面自动化（截图、视觉控制）
│   │   ├── workflows/               # DAG 工作流引擎
│   │   ├── rpa/                    # RPA 自动化引擎
│   │   ├── skills/                  # 技能系统（本地 + ClawHub 远程）
│   │   │   ├── clawhub.py          # 技能市场客户端
│   │   │   ├── registry.json       # 本地技能注册表
│   │   │   ├── office/             # 办公类技能
│   │   │   ├── ops/                # 运维类技能
│   │   │   ├── ec/                 # 电商类技能
│   │   │   └── ai/                 # AI 增强类技能
│   │   └── im_adapter/             # IM 适配器
│   │       ├── main.py             # IM 网关（独立服务）
│   │       ├── adapters/           # 平台适配器（企业微信/飞书/钉钉/Telegram）
│   │       ├── models/             # 统一消息模型
│   │       └── requirements.txt    # IM 适配器依赖
│   └── plugins/                     # 插件目录（运行时加载）
│       └── official/              # 官方插件
├── frontend-vue/                     # Vue 3 前端
│   ├── src/
│   │   ├── api/                    # API 调用层（system.ts 等）
│   │   ├── views/                  # 页面组件（20+ 页面）
│   │   ├── components/             # 可复用组件（BaseButton/Modal/Table 等）
│   │   ├── composables/            # 组合式函数（useTheme 等）
│   │   ├── stores/                 # Pinia 状态管理
│   │   ├── router/                 # Vue Router 配置
│   │   └── App.vue
│   └── dist/                       # 预构建生产版本
├── docs/                            # 文档目录
├── scripts/                         # 运维脚本
├── wanclaw.service                  # systemd 服务配置
├── docker-compose.yml               # Docker 编排
├── Dockerfile                       # 生产镜像
├── Dockerfile.dev                  # 开发镜像
├── build_production.sh             # 生产构建脚本
└── deploy.sh                       # 部署脚本
```

---

## 完整安装

### 方式一：Docker 部署（推荐生产环境）

```bash
# 拉取代码
git clone https://github.com/your-org/wanclaw.git
cd wanclaw

# 编辑配置
cp wanclaw/data/config.example.json wanclaw/data/config.json
# 编辑 wanclaw/data/config.json，填入你的 API Key

# 启动
docker-compose up -d

# 查看状态
docker-compose ps
```

### 方式二：systemd 部署（推荐生产环境）

```bash
# 1. 安装依赖
bash install_all_in_one.sh

# 2. 配置（编辑配置文件）
vim wanclaw/data/config.json

# 3. 安装 systemd 服务
sudo cp wanclaw.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable wanclaw-backend
sudo systemctl start wanclaw-backend

# 4. 配置 Nginx（参考下方）
sudo cp docs/deploy/nginx.conf /etc/nginx/sites-available/wanclaw
sudo nginx -t && sudo systemctl reload nginx
```

### 方式三：手动安装

```bash
# Python 依赖
pip install fastapi uvicorn pydantic httpx websockets pyyaml redis aiofiles

# Node 依赖
cd frontend-vue && npm install && npm run build && cd ..

# 启动后端
cd wanclaw
python -m wanclaw.backend.main
```

---

## 配置指南

### 后端配置

编辑 `wanclaw/data/config.json`（启动后自动创建）：

```json
{
  "ai": {
    "engine": "deepseek",
    "deepseek": {
      "api_key": "sk-your-key",
      "model": "deepseek-chat"
    },
    "qwen": {
      "api_key": "",
      "model": "qwen-plus"
    },
    "zhipu": {
      "api_key": "",
      "model": "glm-4-flash"
    }
  },
  "redis": {
    "url": "redis://localhost:6379"
  },
  "im": {
    "platform": "feishu",
    "feishu": {
      "app_id": "",
      "app_secret": ""
    }
  },
  "notification": {
    "dingtalk": {
      "webhook_url": ""
    }
  }
}
```

### Nginx 配置

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # 前端静态文件
    location / {
        root /path/to/wanclaw/frontend-vue/dist;
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:40710;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

---

## API 参考

所有 API 需在请求头中携带 `Authorization: Bearer <token>`（登录后获取）。

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/admin/login` | 登录（`{"password": "wanclaw"}`） |
| POST | `/api/admin/logout` | 登出 |
| GET | `/api/admin/me` | 当前用户信息 |

### 系统

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/admin/system` | 系统信息 |
| GET | `/api/admin/stats` | 仪表盘统计数据 |
| GET | `/api/admin/analytics` | 分析数据（DAU/漏斗/营收） |
| GET | `/api/admin/config` | 系统配置 |
| PUT | `/api/admin/config` | 更新配置 |

### 租户管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/admin/rbac/roles` | 角色列表 |
| GET | `/api/admin/rbac/users` | 用户列表 |
| POST | `/api/admin/rbac/roles` | 创建角色 |
| GET | `/api/admin/tenant/plans` | 套餐列表 |
| GET | `/api/admin/tenant/tenants` | 租户列表 |

### 工作流

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/admin/workflows` | 列表 |
| POST | `/api/admin/workflows` | 创建 |
| PUT | `/api/admin/workflows/{id}` | 更新 |
| DELETE | `/api/admin/workflows/{id}` | 删除 |

### 任务与日志

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/tasks` | 任务列表 |
| DELETE | `/api/tasks/{id}` | 删除任务 |
| GET | `/api/admin/logs` | 系统日志 |
| GET | `/api/admin/webhook/logs` | Webhook 日志 |

### 技能与插件

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/admin/skills` | 本地技能 |
| GET | `/api/clawhub/skills` | 市场技能（`?source=local\|remote\|all`） |
| POST | `/api/clawhub/sync` | 同步远程技能 |
| POST | `/api/admin/skills/execute` | 执行技能 |
| GET | `/api/plugins` | 插件列表 |
| POST | `/api/marketplace/install` | 安装插件 |

### RPA

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/admin/rpa/tools` | 可用工具列表 |
| POST | `/api/admin/rpa/execute` | 执行 RPA 动作 |

### 容灾

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/admin/health/detail` | 系统健康详情 |
| GET | `/api/admin/failover/status` | 模型容灾状态 |
| GET | `/api/admin/backup/list` | 备份列表 |
| POST | `/api/admin/backup/create` | 创建备份 |
| POST | `/api/admin/backup/restore/{id}` | 恢复备份 |

### 告警

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/admin/alerts/rules` | 告警规则 |
| POST | `/api/admin/alerts/rules` | 创建规则 |
| PUT | `/api/admin/alerts/rules/{id}/toggle` | 启用/禁用规则 |
| GET | `/api/admin/alerts/channels` | 通知渠道 |
| GET | `/api/admin/alerts/history` | 告警历史 |

完整 OpenAPI 文档在运行后访问：`http://localhost:40710/docs`

---

## 前端开发

```bash
cd frontend-vue

# 安装依赖
npm install

# 开发模式（热重载）
npm run dev

# 类型检查
npm run build     # 包含 vue-tsc 类型检查

# 预览构建结果
npm run preview
```

### 新增页面

1. 在 `src/views/` 创建 `.vue` 文件
2. 在 `src/router/index.ts` 添加路由
3. 在 `src/api/system.ts` 添加 API 方法（如需要）

---

## 插件开发

### 插件结构

```
wanclaw/wanclaw/plugins/official/my_plugin/
├── main.py         # 必须：入口文件
├── plugin.json     # 可选：元数据
└── README.md      # 可选：文档
```

### main.py 示例

```python
class MyPlugin:
    name = "my_plugin"
    description = "我的自定义插件"
    version = "1.0.0"

    async def execute(self, params: dict, context: dict) -> dict:
        # 业务逻辑
        return {"status": "success", "result": "done"}
```

### 安装插件

- 通过管理后台「插件市场」页面上传 ZIP
- 或放置到 `wanclaw/plugins/official/` 目录后调用 `POST /api/plugins/{name}/load`

---

## 常见问题

**Q: 启动后端报 `ModuleNotFoundError`？**  
A: 确保在 `wanclaw/wanclaw/` 目录运行，或设置 `PYTHONPATH=/data/wanclaw/wanclaw/wanclaw/backend`。

**Q: 前端构建后访问 404？**  
A: 检查 Nginx 配置中 `root` 是否指向 `frontend-vue/dist/`，并确保 `try_files $uri $uri/ /index.html` 存在。

**Q: IM 适配器无法连接？**  
A: IM Adapter 是独立服务，需要单独启动。参考 `im_adapter/main.py` 的配置说明。

**Q: 如何修改端口？**  
A: 编辑 `wanclaw/backend/main.py` 中的 `uvicorn.run(app, host="0.0.0.0", port=40710)`。

---
**核心开发人员 **
-xinghe
-qianlan
---
**版权所有 © 2026 厦门亦梓科技有限公司 / 厦门万跃科技有限公司**
