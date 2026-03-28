# WanClaw 插件生态索引

> WanClaw V2.0 官方插件完整目录，覆盖电商、IM、办公、AI、数据、运维、工作流等核心场景

---

## 目录

- [概述](#概述)
- [标准插件结构](#标准插件结构)
- [plugin.json 字段参考](#pluginjson-字段参考)
- [权限类型](#权限类型)
- [插件分类索引](#插件分类索引)
  - [电商自动化 (EC)](#电商自动化-ec--14)
  - [IM智能客服 (IM)](#im智能客服-im--15)
  - [办公RPA (Office)](#办公rpa-office--12)
  - [AI增强 (AI)](#ai增强-ai--12)
  - [数据统计 (Data)](#数据统计-data--8)
  - [系统运维 (Ops)](#系统运维-ops--7)
  - [工作流 (Workflow)](#工作流-workflow--6)
  - [插件生态 (Eco)](#插件生态-eco--5)
  - [扩展技能 (Additional)](#扩展技能-additional--22)
- [开发指南](#开发指南)
- [安装命令](#安装命令)

---

## 概述

WanClaw 插件系统基于 Skill 架构设计，支持本地安装、URL 安装和 ClawHub 市场分发。所有插件统一通过 `plugin_manager.execute()` 调用，异步执行，返回标准化结果字典。

**核心特性：**

- 插件隔离：每个插件独立目录、依赖和版本管理
- 权限管控：安装前展示所需权限清单，用户手动确认授权
- 依赖解析：自动处理 `requirements.txt` 中的 Python 依赖
- 热插拔：无需重启服务即可安装/卸载/升级插件
- 双 ID 体系：标准插件使用 `wanclaw.{prefix}_{name}` 前缀；扩展技能使用 `skill.{name}` 前缀

**76 个官方插件**分布于 8 大标准分类，另有 22 个扩展技能插件覆盖办公自动化、AI增强、运维管理、营销获客、管理运营、安全管理等细分场景。

---

## 标准插件结构

每个插件遵循统一目录结构：

```
wanclaw.{plugin_id}/          # 或 skill.{plugin_id}
├── main.py                   # 入口文件（必须）
├── plugin.json               # 元数据（可选，建议提供）
├── requirements.txt          # Python 依赖（可选）
└── README.md                # 文档（可选）
```

**main.py 入口规范：**

```python
class MyPlugin:
    name = "my_plugin"
    description = "插件描述"

    def execute(self, params):
        # 业务逻辑
        return {"status": "success", "result": "执行成功"}
```

调用方式：

```python
result = await plugin_manager.execute("wanclaw.{plugin_id}", {"action": "xxx"})
# 或
result = await plugin_manager.execute("skill.{plugin_id}", {"action": "xxx"})
```

---

## plugin.json 字段参考

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
  "level": "intermediate",
  "author": "WanClaw",
  "category": "电商自动化"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `plugin_id` | string | 是 | 全局唯一标识，前缀为 `wanclaw.` 或 `skill.` |
| `plugin_name` | string | 是 | 插件显示名称 |
| `plugin_type` | string | 是 | 类型：`skill` |
| `version` | string | 是 | 语义化版本，如 `2.0.0` |
| `compatible_wanclaw_version` | string | 否 | 兼容的 WanClaw 版本范围 |
| `permissions` | array | 是 | 权限清单，详见下表 |
| `dependencies` | array | 否 | Python 外部依赖 |
| `keywords` | array | 否 | 搜索关键词 |
| `level` | string | 否 | 难度：`beginner` / `intermediate` / `advanced` |
| `author` | string | 否 | 作者 |
| `category` | string | 否 | 分类名称 |

---

## 权限类型

| 权限 | 说明 | 典型用途 |
|------|------|---------|
| `network` | 允许网络请求（HTTP/WebSocket） | API 调用、消息推送 |
| `database` | 允许数据库读写 | 订单查询、数据统计 |
| `filesystem:read` | 允许读取本地文件 | 文档处理、配置读取 |
| `filesystem:write` | 允许写入本地文件 | 文件导出、备份写入 |
| `email` | 允许邮件收发操作 | 邮件分类、自动化发送 |
| 无需特殊权限 | 不请求任何敏感权限 | 本地计算型插件 |

> 安装前所有需要权限的插件均会通过 `wanclaw.eco_permission_confirm` 展示权限清单，用户手动确认后方可激活。

---

## 插件分类索引

---

### 电商自动化 (EC) — 14

淘宝、京东、拼多多、抖音等多平台电商订单处理、库存管理、物流同步、售后自动化。

- `wanclaw.ec_auto_review_reply` — 评价智能自动回复
- `wanclaw.ec_data_mask` — 订单数据脱敏导出
- `wanclaw.ec_order_close` — 超时订单自动关闭
- `wanclaw.ec_order_remark` — 淘宝订单自动备注
- `wanclaw.ec_presale_split` — 预售订单自动拆分
- `wanclaw.ec_product_auto_listing` — 商品自动上下架
- `wanclaw.ec_refund_auto` — 拼多多售后自动退款
- `wanclaw.ec_review_monitor` — 差评自动监控提醒
- `wanclaw.ec_rto_ledger` — 退换货自动台账
- `wanclaw.ec_shipment_sync` — 抖店自动发货同步
- `wanclaw.ec_shipping_fee` — 运费智能计算
- `wanclaw.ec_stock_alert` — 库存阈值自动告警
- `wanclaw.ec_tracking_auto` — 物流单号自动识别
- `wanclaw.ec_unified_order_view` — 多店铺订单统一视图

---

### IM智能客服 (IM) — 15

企业微信、钉钉、飞书、Telegram 等多平台消息聚合、自动化回复、客户管理。

- `wanclaw.im_anti_ads` — 广告违规自动踢人
- `wanclaw.im_blacklist_sync` — 跨平台黑名单同步
- `wanclaw.im_friend_auto` — 好友自动通过与打标
- `wanclaw.im_group_activity` — 群活跃度统计分析
- `wanclaw.im_inbox_unified` — 多平台消息统一收件箱
- `wanclaw.im_keyword_reply` — 关键词触发自动回复
- `wanclaw.im_message_priority` — 客户消息智能分级
- `wanclaw.im_mute_schedule` — 静音时段定时开关
- `wanclaw.im_profile_auto` — 客户画像自动记录
- `wanclaw.im_quick_reply` — 快捷回复模板库
- `wanclaw.im_schedule_broadcast` — 定时群发消息
- `wanclaw.im_transfer_handoff` — 客服会话智能转接
- `wanclaw.im_voice_to_text` — 语音消息转文字
- `wanclaw.im_welcome_auto` — 新人入群自动欢迎
- `skill.wechat_group_monitor` — 微信群监控（关键词提醒、群活跃度统计）

---

### 办公RPA (Office) — 12

Excel/Word/PDF/邮件等办公文档的批量处理、自动化操作。

- `wanclaw.office_batch_rename` — 批量文件规则重命名
- `wanclaw.office_contract_extract` — 合同要素智能提取
- `wanclaw.office_deduplicate` — 表格重复数据去重
- `wanclaw.office_email_auto_classify` — 邮件自动分类归档
- `wanclaw.office_excel_diff` — Excel批量对比差异
- `wanclaw.office_folder_auto_sort` — 文件夹自动整理归档
- `wanclaw.office_form_auto_fill` — 网页表单自动填充
- `wanclaw.office_image_processor` — 图片批量处理
- `wanclaw.office_multi_table_merge` — 多表格自动汇总
- `wanclaw.office_pdf_watermark` — PDF批量水印处理
- `wanclaw.office_print_queue` — 打印任务自动队列
- `wanclaw.office_web_scraper` — 网页数据定时采集

---

### AI增强 (AI) — 12

大模型驱动的文案生成、OCR识别、翻译、摘要、TTS等 AI 能力增强。

- `wanclaw.ai_emotion_detect` — 对话情绪识别
- `wanclaw.ai_image_moderation` — 图片内容安全审核
- `wanclaw.ai_intent_classify` — AI意图识别
- `wanclaw.ai_ocr_high_precision` — 高精度OCR识别
- `wanclaw.ai_product_copy` — AI商品文案生成
- `wanclaw.ai_reply_suggest` — AI客服话术推荐
- `wanclaw.ai_report_auto` — AI自动生成经营报告
- `wanclaw.ai_text_summary` — 长文本自动摘要
- `wanclaw.ai_translate` — 多语言自动翻译
- `wanclaw.ai_tts_broadcast` — 语音合成播报
- `skill.copywriter_ai` — AI文案生成（广告语、朋友圈、产品介绍、邮件模板）
- `skill.nlp_task_generator` — NLP任务生成器（文本分类、情感分析、实体识别）
- `skill.ocr_processor` — OCR文字识别（图片转文字、PDF转文字、表格识别）
- `skill.workflow_chain` — 工作流链式编排（多技能链式执行、条件分支、循环处理）

---

### 数据统计 (Data) — 8

销售、客服、库存、渠道等多维度经营数据分析与推送。

- `wanclaw.data_agent_stats` — 客服接待量实时报表
- `wanclaw.data_channel_stats` — 客户来源渠道分析
- `wanclaw.data_chart_export` — 可视化图表导出
- `wanclaw.data_daily_push` — 每日经营数据推送
- `wanclaw.data_inventory_turnover` — 库存周转率分析
- `wanclaw.data_plugin_usage` — 插件使用数据统计
- `wanclaw.data_sales_stats` — 经营数据自动统计
- `wanclaw.data_sync_sheets` — 数据同步至飞书/钉钉

---

### 系统运维 (Ops) — 7

服务器资源监控、日志管理、备份恢复、故障自愈等运维自动化。

- `wanclaw.ops_auto_restart` — 服务崩溃自动重启
- `wanclaw.ops_config_backup` — 配置文件自动备份
- `wanclaw.ops_cpu_mem_alert` — 资源超限告警
- `wanclaw.ops_disk_cleanup` — 磁盘空间自动清理
- `wanclaw.ops_log_rotate` — 日志自动切割归档
- `wanclaw.ops_network_reconnect` — 网络断连自动重连
- `wanclaw.ops_remote_restart` — 远程服务一键重启

---

### 工作流 (Workflow) — 6

基于 DAG 引擎的可视化编排、模板市场、自动重试、条件分支、结果通知。

- `wanclaw.wf_auto_retry` — 失败步骤自动重试
- `wanclaw.wf_condition_branch` — 条件分支工作流
- `wanclaw.wf_result_notify` — 执行结果自动通知
- `wanclaw.wf_schedule_trigger` — 定时任务触发
- `wanclaw.wf_template_import` — 工作流模板市场
- `wanclaw.wf_visual_builder` — 可视化工作流设计器

---

### 插件生态 (Eco) — 5

ClawHub 生态站核心功能：一键安装、离线导入、权限确认、评分评论、排行榜。

- `wanclaw.eco_offline_import` — 本地插件离线导入
- `wanclaw.eco_oneclick_install` — 插件一键安装升级
- `wanclaw.eco_permission_confirm` — 插件权限手动确认
- `wanclaw.eco_plugin_rating` — 插件评分与评论
- `wanclaw.eco_plugin_ranking` — 插件排行榜

---

### 扩展技能 (Additional) — 22

22 个扩展技能插件，涵盖办公自动化、AI增强、运维管理、营销获客、管理运营、安全管理等细分领域，补充标准分类未覆盖的场景。

#### 办公自动化 (5)

- `skill.batch_file_processor` — 批量文件处理（格式转换、压缩解压、批量重命名）
- `skill.contract_extractor` — 合同要素提取（甲乙方、金额、期限、违约条款）
- `skill.email_automation` — 邮件自动化（定时发送、批量群发、邮件模板）
- `skill.email_processor` — 邮件处理（批量读取、分类过滤、自动回复）
- `skill.excel_processor` — Excel处理（多表合并、拆分、去重、汇总，生成报表）
- `skill.file_manager` — 文件管理器（批量重命名、分类整理、搜索查找）
- `skill.pdf_processor` — PDF处理（合并拆分、提取文字、添加水印）
- `skill.spreadsheet_handler` — 表格处理器（数据透视、公式计算、图表生成）

#### AI增强 (4)

- `skill.copywriter_ai` — AI文案生成（广告语、朋友圈、产品介绍、邮件模板）
- `skill.nlp_task_generator` — NLP任务生成器（文本分类、情感分析、实体识别）
- `skill.ocr_processor` — OCR文字识别（图片文字识别、PDF转文字、表格识别）
- `skill.workflow_chain` — 工作流链式编排（多技能链式执行、条件分支）

#### 运维管理 (5)

- `skill.backup` — 数据备份（文件备份、定时备份、增量备份、压缩存储）
- `skill.backup_manager` — 备份管理（备份策略、备份恢复、备份验证）
- `skill.health_checker` — 系统健康检查（磁盘空间、CPU、内存，异常告警）
- `skill.log_cleaner` — 日志清理（过期日志清理、磁盘空间释放）
- `skill.log_viewer` — 日志查看器（日志搜索、实时tail、关键词过滤）
- `skill.process_monitor` — 进程监控（进程列表、CPU/内存占用、异常检测）

#### 营销获客 (3)

- `skill.competitor_monitor` — 竞品动态监控（竞争对手追踪、价格监控、新品监控）
- `skill.customer_importer` — 客户数据导入（批量导入、重复检测、数据验证）
- `skill.media_processor` — 媒体内容处理（图片压缩、视频转码、音频提取）

#### 管理运营 (3)

- `skill.attendance_processor` — 考勤处理（导入打卡记录、自动算工时、生成工资表）
- `skill.inventory_manager` — 库存管理（库存查询、预警提醒、出入库记录、盘点）
- `skill.meeting_notes_generator` — 会议纪要生成（自动生成结构化纪要、待办事项）
- `skill.order_sync` — 订单同步（多平台订单拉取、状态同步、异常告警）

#### 安全管理 (1)

- `skill.security_scanner` — 安全扫描（代码安全扫描、敏感信息检测、漏洞检测）

---

## 开发指南

### 创建自定义插件

```python
# wanclaw/plugins/official/my_custom_plugin/main.py

class MyPlugin:
    name = "my_custom_plugin"
    description = "我的自定义插件"

    def execute(self, params):
        # 业务逻辑
        return {"status": "success", "result": "执行成功"}
```

对应的 `plugin.json`：

```json
{
  "plugin_id": "wanclaw.my_custom_plugin",
  "plugin_name": "我的自定义插件",
  "plugin_type": "skill",
  "version": "1.0.0",
  "permissions": ["network"],
  "level": "beginner"
}
```

### 插件目录

将插件放入 `wanclaw/plugins/official/{plugin_id}/` 目录后，执行安装命令即可自动注册。

### 注意事项

- 插件 ID 全局唯一，建议使用 `{prefix}_{name}` 命名规范
- 所有外部依赖必须在 `requirements.txt` 中声明
- 敏感权限（如 `filesystem:write`、`email`）需在 `plugin.json` 中明确列出
- 建议提供 `README.md`，包含功能说明、权限说明、使用示例

---

## 安装命令

```bash
# 通过 ClawHub 生态站一键安装
wanclaw plugin install wanclaw.ec_order_remark

# 通过 URL 安装（支持 ZIP 包）
wanclaw plugin install https://example.com/plugin.zip

# 本地离线导入
wanclaw plugin import /path/to/plugin.zip

# 查看已安装插件
wanclaw plugin list

# 升级插件
wanclaw plugin upgrade wanclaw.ec_order_remark

# 卸载插件
wanclaw plugin uninstall wanclaw.ec_order_remark
```

---

**版权所有 © 2025-2026 厦门亦梓科技有限公司 / 厦门万跃科技有限公司**  
**Copyright © 2025-2026 Xiamen Yizi Technology Co., Ltd. / Xiamen Wanyue Technology Co., Ltd. All Rights Reserved.**
