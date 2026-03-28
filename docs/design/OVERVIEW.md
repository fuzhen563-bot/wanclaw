# WanClaw V2.0 — System Architecture Overview

> **⚠️ Replacement Notice:** This document supersedes `wanclaw/wanclaw/README.md`, which is outdated and describes a deprecated SQLite/3-layer architecture. The authoritative source of truth is the main project README at the repository root.

---

## Overview

WanClaw V2.0 is an enterprise-grade AI assistant platform built for distributed, multi-tenant deployment. It combines multi-model AI routing, browser/desktop RPA automation, DAG-based workflow orchestration, and cross-platform IM integration into a unified system.

The platform targets businesses that need to automate customer service, internal operations, and e-commerce workflows across multiple IM channels — with full RBAC permission control, usage analytics, and a tiered pricing model.

Key differentiators from V1.x:
- **Redis-centric distributed architecture** replacing the earlier SQLite/3-layer model
- **12 independent backend modules** with clear separation of concerns
- **76 official plugins** covering e-commerce, IM, office automation, AI enhancement, and more
- **Multi-model AI routing** with automatic failover across 5 providers
- **Dual RPA engines** (Playwright + Selenium) for browser automation, plus desktop vision automation

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            Clients / External                              │
│            Web Console    │    IM Platforms (5)    │    API Consumers      │
└──────────────┬────────────┴───────────┬────────────┴──────────┬───────────┘
               │                       │                         │
               └───────────────────────┼─────────────────────────┘
                                       │
┌──────────────────────────────────────▼───────────────────────────────────┐
│                           API Gateway                                      │
│                    (Auth · Rate Limiting · Routing · Logging)              │
└──────┬────────────┬────────────┬────────────┬────────────┬───────────────┘
       │            │            │            │            │
┌──────▼─────┐ ┌────▼────┐ ┌────▼──────┐ ┌───▼────┐ ┌─────▼──────────────┐
│  Gateway    │ │ Tasks   │ │  AI       │ │ Workflows│ │   IM Adapter      │
│  (Redis     │ │ (Redis  │ │  (ReAct   │ │  (DAG    │ │   (5 platforms)   │
│   Pub/Sub)  │ │ Streams)│ │   Agent   │ │   Engine)│ │                   │
└─────────────┘ └─────────┘ │  + Router)│ └─────────┘ └───────────────────┘
                             └───────────┘
┌──────────────┐ ┌───────────┐ ┌──────────────┐ ┌────────────┐ ┌───────────┐
│  Auth        │ │Analytics  │ │ Notification │ │   Audit    │ │  Skills   │
│  (RBAC +     │ │(DAU/MAU,  │ │ (DingTalk,   │ │(GDPR, full │ │(76 plugins│
│   Tenant)    │ │ MRR/ARR)  │ │  Feishu,     │ │  chain     │ │  registry)│
│              │ │           │ │  email...)   │ │  logging)  │ │           │
└──────────────┘ └───────────┘ └──────────────┘ └────────────┘ └───────────┘
                                       │
                             ┌─────────┴─────────┐
                             │       Redis        │
                             │ (Pub/Sub · Streams │
                             │  · Hash · Sorted   │
                             │  Set · Connection  │
                             │       Pool)         │
                             └────────────────────┘
```

### Data Flow

1. **Inbound**: Requests arrive via the API Gateway (from web clients, IM platform webhooks, or API consumers) and are authenticated, rate-limited, and routed.
2. **Processing**: The Gateway dispatches to the appropriate module. Long-running tasks are enqueued to the Redis-based Task Queue. Complex multi-step tasks trigger the Workflow Engine.
3. **AI Layer**: The AI module uses the ReAct Agent for planning and the Model Router for multi-provider LLM calls (DeepSeek → Qwen → GLM4 → Moonshot → Ollama), with automatic failover on 429/5xx errors.
4. **Automation**: RPA tasks use Playwright or Selenium for browser automation, or the desktop automation stack (InputController + VisionController) for local UI interaction.
5. **Outbound**: The Notification Manager pushes results to configured channels. The Audit module records all operations. Analytics are aggregated continuously.

---

## Module Structure

The backend is organized into 12 independently deployable modules under `wanclaw/backend/`:

| Module | Purpose | Key Classes |
|---|---|---|
| **gateway** | Distributed message routing via Redis Pub/Sub. Handles node discovery, heartbeat (30s TTL), and load-balanced message broadcast/unicast. | `DistributedGateway`, `SessionStore`, `MessageQueue` |
| **tasks** | Priority queue on Redis Sorted Sets. Supports checkpoint/resume, exponential-backoff retry (max 3), and 6 task states. | `TaskQueue` |
| **ai** | ReAct Agent (Thought/Action/Observation loop with 6 built-in tools), multi-model `ModelRouter` (5 providers, auto-failover), unified `OllamaClient` (OpenAI-compatible), `AutoReply` engine, `Embedding` + semantic memory, `Security` filter. | `ReActAgent`, `ModelRouter`, `OllamaClient`, `Embedding`, `AutoReply` |
| **workflows** | DAG engine using Kahn topological sort. Supports 13 node types (START, TASK, CONDITION, PARALLEL, HTTP, SKILL, SUBWORKFLOW, etc.) with configurable parallelism (default 5), variable substitution `${var}`, and 4 error strategies. | `WorkflowEngine`, `TaskExecutor`, `ParallelExecutor` |
| **automation** | Desktop RPA: `InputController` (mouse/keyboard via pyautogui with LRU action cache), `VisionController` (OCR via tesseract/easyocr, template matching, smart wait), `Sandbox` (AST-level code validation, 4 security modes, Docker isolation), `WindowManager`, `AppLauncher`. | `InputController`, `VisionController`, `AutomationSandbox` |
| **rpa** | Browser automation: Playwright + Selenium dual-engine `BrowserPool` (5 connections default), supports Chromium/Firefox/WebKit. Full element targeting (ID/CSS/XPath/text/ARIA/label), `SmartElementLocator` with AI-assisted fallback. | `BrowserDriver`, `SeleniumDriver`, `BrowserPool` |
| **auth** | RBAC with 40+ permission types and 4 default roles (Super Admin / DevOps / Developer / Agent). API key authentication with SHA-256 hashing. | `AuthService`, `RBAC` |
| **tenant** | Multi-tenant isolation with 4-tier pricing (Free/Basic/Pro/Enterprise), quota enforcement per plan, and tenant-scoped data partitioning. | `TenantService` |
| **notification** | Multi-channel alert dispatcher: DingTalk, Feishu, email, SMS, Webhook, WeCom, Telegram. Alert rules with condition expressions, cooldown to prevent alert storms, level-based filtering. | `NotificationManager` |
| **analytics** | Redis-based metrics collection (Counter/Gauge/Histogram/Rate). DAU/MAU, conversion funnels, session stats. Revenue analytics: MRR, ARR, ARPU. Auto-generated daily/weekly/monthly reports. Real-time QPS and latency (P99) monitoring. | `AnalyticsDashboard`, `RevenueAnalytics` |
| **api_gateway** | Central entry point for all external traffic. Handles API key auth, per-user/per-IP/per-key/global rate limiting, request logging, and middleware chain. | `APIGateway` |
| **audit** | Full-chain operation logging (60+ action types: user, tenant, skill, workflow, message, system). GDPR compliance reports, security audit reports (failed ops, suspicious IPs), user access reports with data export. | `AuditService` |
| **skills** | Plugin marketplace client (ClawHub), local registry (`registry.json`), organized into office/ops/ai subdirectories. | `ClawHub`, `Marketplace` |
| **im_adapter** | Unified gateway with platform-specific adapters for 5 IM platforms. Standardized `UnifiedMessage` model. Async message handling with connection pooling and health monitoring. | `IMGateway`, adapters (WeCom, Feishu, QQ, WeChat, Telegram) |

---

## Tech Stack

| Layer | Technology | Usage in WanClaw |
|---|---|---|
| **Message Bus** | Redis 7+ | Pub/Sub (gateway broadcast), Streams (task queue), Sorted Sets (priority queue), Hash (session), connection pooling |
| **AI Models** | DeepSeek / Qwen / GLM4 / Moonshot / Ollama | OpenAI-compatible API interface via unified `OllamaClient`. Auto-failover via `ModelRouter` |
| **Browser RPA** | Playwright + Selenium | Dual-engine browser pool with element targeting and AI-assisted fallback |
| **Desktop Automation** | pyautogui + OpenCV + Tesseract OCR / EasyOCR | Mouse/keyboard control, vision-based element location, OCR (80+ languages) |
| **Screenshots** | mss → pyscreenshot → PIL.ImageGrab → pyautogui | Fallback chain from fastest to most compatible |
| **Workflow Engine** | Kahn topological sort + asyncio | DAG validation, parallel execution, error recovery |
| **Security Sandbox** | AST analysis + Docker | Code validation, container isolation, OWASP-based command blocking |
| **HTTP Client** | httpx | Async HTTP for AI API calls |
| **Config** | JSON + env var `${VAR}` substitution | Single `config.json` at `~/.wanclaw/` |
| **Frontend** | HTML (Vue/Element UI ready) | Admin console, plugin marketplace, main dashboard |
| **Deployment** | Docker + docker-compose | One-command production deployment |

---

## Plugin Ecosystem

WanClaw ships with **76 official plugins** organized into 8 categories:

| Category | Count | Highlights |
|---|---|---|
| **E-commerce Automation** | 14 | Auto-remark Taobao orders, auto-refund on Pinduoduo, Douyin shipment sync, inventory threshold alerts |
| **IM Smart Customer Service** | 14 | Auto-approve friends, keyword-triggered replies, ad kick, chat transfer |
| **Office RPA** | 12 | Excel diff, PDF watermark, contract element extraction, auto form fill |
| **AI Enhancement** | 10 | AI product copy, reply suggestions, high-precision OCR, TTS broadcast |
| **Data Statistics** | 8 | Sales stats, agent reports, channel analytics, plugin usage stats |
| **System Operations** | 7 | CPU/memory alerts, disk cleanup, remote restart |
| **Workflow** | 6 | Visual DAG builder, auto-retry, conditional branching, result notification |
| **Plugin Ecosystem** | 5 | One-click install, permission confirm, plugin rating/ranking |

### Plugin Standard

Each plugin is a self-contained directory with `main.py` as the entry point and optional `plugin.json` metadata:

```json
{
  "plugin_id": "wanclaw.ec_order_remark",
  "plugin_name": "淘宝订单自动备注",
  "plugin_type": "skill",
  "version": "2.0.0",
  "compatible_wanclaw_version": ">=2.0.0",
  "permissions": ["network", "database"],
  "dependencies": ["openpyxl"],
  "keywords": ["淘宝", "订单备注"],
  "level": "intermediate"
}
```

Permissions are explicitly declared (`network`, `database`, `filesystem:read`, `filesystem:write`, `email`) and enforced by the sandbox.

### Installation

```bash
# Via ClawHub marketplace
wanclaw plugin install wanclaw.ec_order_remark

# Via direct URL
wanclaw plugin install https://example.com/plugin.zip
```

---

## Pricing Tiers

| Plan | Price | Users | Stores | API Calls | Storage | Key Features |
|---|---|---|---|---|---|---|
| **Free** | ¥0 | 3 | 1 | 500/month | 512 MB | Basic IM + AI reply |
| **Basic** | ¥99/mo | 10 | 3 | 10,000/month | 5 GB | + Workflow engine |
| **Professional** | ¥299/mo | 50 | 10 | 100,000/month | 50 GB | + RPA + Analytics |
| **Enterprise** | ¥999/mo | Unlimited | Unlimited | Unlimited | Unlimited | + Dedicated support + Custom development |

---

*WanClaw V2.0 — Copyright © 2025-2026 Xiamen Yizi Technology Co., Ltd. / Xiamen Wanyue Technology Co., Ltd.*
