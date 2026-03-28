# WanClaw 升级计划 — 平替 OpenClaw

## 差距分析

| 模块 | OpenClaw 现状 | WanClaw 现状 | 差距 | 优先级 |
|------|--------------|-------------|------|--------|
| IM 通道 | 25+ 平台 | 12 平台 | 13+ 缺失 | P0 |
| 网关架构 | WS 控制平面 + 会话 + 状态 | 简单 REST + WebSocket | 严重不足 | P0 |
| 技能市场 | ClawHub (5400+ 技能) | 27 内置技能 | 无市场 | P1 |
| AI 引擎 | OpenAI/Claude/本地 | Ollama + 6 种云 API | 已具备 | P1 |
| 语音支持 | TTS/STT + 语音通话 | 无 | 缺失 | P2 |
| 原生 App | macOS/iOS/Android | 无 | 可延后 | P3 |
| Web UI | 控制面板 + Canvas | 单页 SPA | 需升级 | P1 |
| 定时任务 | 内置 Cron | 无 | 缺失 | P1 |
| Webhook | 内置 Webhook 管理 | 基础支持 | 需升级 | P1 |
| 插件系统 | 热加载插件 | 静态技能 | 需升级 | P1 |

## 第一阶段：核心能力补齐 (P0)

### 1.1 IM 通道扩展

新增 13 个通道（按优先级）：

**即时通讯：**
- WhatsApp (via Baileys/web-whatsapp)
- iMessage (via BlueBubbles API)
- Signal (via signal-cli)
- Slack (via Bolt SDK)
- Discord (via discord.js)
- Microsoft Teams (via Bot Framework)
- Matrix (via matrix-js-sdk)
- LINE (via LINE Messaging API)
- IRC (via irc-framework)

**协作平台：**
- Microsoft Teams
- Mattermost
- Nextcloud Talk

**社交平台：**
- Twitch
- Nostr

### 1.2 网关架构升级

```
当前架构:
  Client → FastAPI → Adapter → Platform

目标架构:
  Client → Gateway (WS Control Plane)
              ├── Session Manager
              ├── Presence Manager
              ├── Message Router
              ├── Cron Scheduler
              ├── Webhook Manager
              └── Plugin Loader
                    ├── Adapter (WhatsApp)
                    ├── Adapter (Telegram)
                    ├── Adapter (Discord)
                    └── ... (热加载)
```

### 1.3 ClawHub 技能市场

- 技能注册/发现/安装 API
- 技能版本管理
- 技能安全审计（沙箱执行）
- 社区贡献流程

## 第二阶段：功能增强 (P1)

### 2.1 定时任务系统
- Cron 表达式支持
- 定时技能执行
- 定时消息发送

### 2.2 Webhook 管理
- Webhook 注册/验证/分发
- 安全签名验证
- 事件过滤

### 2.3 插件热加载
- 动态加载/卸载技能
- 插件隔离（沙箱）
- 依赖管理

## 第三阶段：体验升级 (P2)

### 3.1 语音支持
- TTS: OpenAI TTS / Azure Speech / 本地模型
- STT: Whisper / 本地模型
- 语音通话适配

### 3.2 Canvas 渲染
- 动态内容渲染
- 图表/表格可视化
- Markdown 渲染

## 第四阶段：生态建设 (P3)

### 4.1 原生 App
- macOS App (Electron/Tauri)
- 移动端 (React Native/Flutter)

### 4.2 社区建设
- 文档站
- 插件市场
- 论坛/Discord 社区

---

## 实施策略

1. **不重写，增量升级** — 保留现有代码，逐步添加
2. **兼容 OpenClaw 技能格式** — 让 WanClaw 能运行 OpenClaw 社区技能
3. **云原生优先** — Docker/K8s 部署，适合中小企业
4. **中文优先** — 保持中文界面和文档优势
