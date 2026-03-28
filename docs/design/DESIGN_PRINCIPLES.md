---
title: WanClaw Design Principles
version: "1.0"
date: 2026-03-22
---

# WanClaw Design Principles

*WanClaw — Lightweight AI Assistant for Small and Medium Enterprises*

---

## 1. Project Background

WanClaw is a lightweight AI assistant system built on the open-source OpenClaw理念, specifically customized for small and medium enterprises (SMEs). It centers on four pillars: low cost, low barrier to entry, needs-first prioritization, and security.

---

## 2. Core Design Principles

| # | Principle | Description |
|---|-----------|-------------|
| 1 | **Low-Cost Deployment** | Prioritize open-source technologies and a simplified architecture; avoid complex components to reduce development and operations costs. |
| 2 | **Low-Barrier Development** | No professional ops team required; supports one-click deployment and visual operation, adapted for non-technical users. |
| 3 | **Needs-First Priority** | Focus on daily office work, basic operations, and simple business automation; avoid feature bloat. |
| 4 | **Security & Control** | Implement baseline security; avoid high-risk operations; adapt to SME data privacy needs. |
| 5 | **Flexible Expansion** | Reserve simple extension interfaces so custom features can be added quickly as the business grows. |

> These principles are shared across both source documents and reflect the guiding philosophy for every architectural and implementation decision.

---

## 3. Overall Architecture

WanClaw follows a simplified three-layer architecture designed for easy maintenance.

### 3.1 Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Access Layer                         │
│  ┌──────────────────┐  ┌─────────────────────────────┐  │
│  │  Web Console     │  │  IM Adapter (WeCom/DingTalk)│  │
│  │  (Vue.js +       │  │                             │  │
│  │   Element UI)    │  │                             │  │
│  └──────────────────┘  └─────────────────────────────┘  │
│              Unified interaction, multi-platform        │
├─────────────────────────────────────────────────────────┤
│                     Execution Layer                      │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────┐  │
│  │ Skill        │  │ Lightweight   │  │ Task        │  │
│  │ Manager      │  │ Sandbox       │  │ Scheduler   │  │
│  └──────────────┘  └───────────────┘  └─────────────┘  │
│     Skill load/     Safe isolation    Simple task       │
│     execution       Low config        on/off toggle     │
├─────────────────────────────────────────────────────────┤
│                       Data Layer                         │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────┐  │
│  │ SQLite DB    │  │ Config Files  │  │ Audit Logs  │  │
│  │ (local store)│  │               │  │             │  │
│  └──────────────┘  └───────────────┘  └─────────────┘  │
│   No DB server   Plain-text config  Action trace       │
│   needed         Low maintenance   Basic encryption    │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Architecture Design Highlights (SME-Adapted)

| Layer | Core Components | Core Functions | Design Highlights |
|-------|----------------|----------------|-------------------|
| **Access Layer** | Web Console, WeCom/DingTalk Adapter | Unified interaction entry, multi-terminal simple operations | No separate client development needed; reuse existing enterprise IM tools |
| **Execution Layer** | Skill Manager, Lightweight Sandbox, Task Scheduler | Skill loading/execution, simple task decomposition, safe isolation | Simplified sandbox config, lower ops difficulty, one-click enable/disable Skill |
| **Data Layer** | Local config files, simple audit logs | Store basic configs, record operation logs | No DB deployment needed; local storage reduces maintenance cost |

---

## 4. Technology Stack

| Category | Technology | Rationale |
|----------|-----------|-----------|
| Backend | Python + FastAPI | Low barrier, fast development |
| Frontend | Vue.js + Element UI | Friendly interface |
| Database | SQLite | No ops required, local storage |
| Containerization | Docker Compose | Simplified deployment |
| Dependency Management | pip + requirements.txt | Standard, lightweight |

---

## 5. Core Features

### 5.1 Essential Features (Must-Have)

| Category | Features | Use Case | Difficulty |
|----------|---------|----------|------------|
| **Office Automation Skills** | File management (batch rename, search, format convert), Email automation (bulk send, filter, auto-reply), Spreadsheet processing (statistics, batch fill, format unify) | Admin, finance, operations — reduce repetitive daily tasks | Low |
| **Basic System Ops Skills** | Process monitoring (view processes, simple restart), Log viewing (filter system/app logs, quick issue diagnosis), Simple backup (local files, config files) | SMEs without dedicated ops — handle basic server issues | Low |
| **Interaction & Control** | Web Console (visual Skill operation, execution status), IM Adapter (send commands via WeCom/DingTalk, receive results), One-click start/stop (quick Claw service management) | Accessible to all staff, no server login needed | Low |
| **Basic Security** | High-risk operation interception (block dangerous commands, limit file access), Operation logs (all executions traceable), Permission control (admin vs. regular user, regular users cannot modify) | Protect enterprise data and server safety, prevent accidents | Low |

### 5.2 Optional Extended Features (Phase Later)

| Category | Features | Suitable For | Difficulty |
|----------|---------|-------------|------------|
| **Browser Automation Skills** | Screenshot capture, simple data scraping (industry news, client info), form auto-submission | Marketing, sales — gather industry data, simplify form workflows | Medium |
| **Business Adapter Skills** | Simple order statistics, customer info sync, inventory alerts (integrate with enterprise Excel/sheets) | Sales, warehouse — simplify business data processing | Medium |
| **Advanced Ops** | Server resource monitoring (CPU/memory), auto-alert on anomalies, one-click rollback | SMEs with lightweight server clusters | Medium |
| **Custom Skill Extension** | Simple SDK for enterprises to develop proprietary Skills quickly | Enterprises with dev capability and special business needs | Medium |

---

## 6. Development Notes

1. **Cost Control** — Prioritize open-source technologies; no paid components. No complex database deployment needed; local storage is sufficient.
2. **Barrier Control** — Avoid complex code development; use templates and visual tools so non-technical staff can operate the system.
3. **Security Baseline** — Do not pursue high-end security mechanisms, but must block high-risk commands and log all operations to prevent data leaks and server failures.
4. **Maintainability** — Keep code clean and well-commented; simplify deployment procedures so non-professional teams can maintain the system afterward.
5. **Iteration Pace** — Complete essential features first and deploy; then gradually add optional extended features based on enterprise needs. Avoid overloading the initial development cycle.

---

## 7. Key Technical Points

### 7.1 Security Technologies

| Point | Description |
|-------|-------------|
| Process Isolation | Prevent Skills from affecting each other |
| Sandbox Execution | Restrict system access permissions |
| Audit Logging | Complete operation traceability |
| RBAC | Role-based access control |

### 7.2 Extension Technologies

| Point | Description |
|-------|-------------|
| Plugin Architecture | Support dynamic Skill loading |
| API Gateway | Unified interface management |
| Config Hot-Reload | Update config without restart |
| Template Engine | Rapid Skill creation |

### 7.3 Operations Technologies

| Point | Description |
|-------|-------------|
| Health Checks | System status monitoring |
| Log Collection | Centralized log management |
| Backup & Recovery | Data safety guarantee |
| Performance Monitoring | System resource tracking |

---

## 8. Risk Assessment

| Category | Risk | Mitigation |
|----------|------|------------|
| **Technical** | Security sandbox vulnerabilities | Multi-layer defense mechanism; regular security audits |
| **Execution** | Insufficient SME technical capability | Detailed documentation; simplified deployment process |
| **Operations** | Difficult system failure recovery | Robust backup/recovery mechanism; 24/7 technical support |

---

## 9. Success Criteria

| Metric | Target |
|--------|--------|
| System uptime | > 99% |
| Skill execution success rate | > 95% |
| System response time | < 3 seconds |
| User satisfaction score | > 4.5 / 5 |
| Ops cost reduction | > 30% |

---

## 10. Expansion Roadmap

### Short-Term (Within 3 Months)
- More IM platform support
- Enhanced security policies
- Performance optimization

### Mid-Term (Within 6 Months)
- Skill marketplace
- Multi-tenant support
- Advanced analytics reports

### Long-Term (Within 1 Year)
- Enhanced AI capabilities
- Cloud collaboration
- Ecosystem partnerships

---

## Appendix: Source Files Reference

This document merges content from two original Chinese design documents:

- `wanclaw设计指南.txt` — Core design principles, architecture, phased plan, features, dev notes, deliverables
- `wanclaw设计清单.txt` — Background, design principles, tech stack, detailed checklist, deliverables, timeline, key tech points, risk assessment, success criteria, expansion plans

**Document Version**: 1.0
**Created**: 2026-03-22
**Status**: Initial version
