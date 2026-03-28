#!/usr/bin/env python3
"""
WanClaw 官方插件打包脚本
将 27 个内置技能转换为标准插件格式
"""

import os
import json
import shutil
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/data/wanclaw/wanclaw/wanclaw/backend/skills")
OUTPUT_DIR = Path("/data/wanclaw/wanclaw/wanclaw/plugins/official")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


SKILL_DEFINITIONS = {
    # office
    "excel_processor": {
        "class": "ExcelProcessorSkill",
        "name": "Excel处理",
        "description": "Excel处理：多表合并、拆分、去重、筛选、排序、汇总，生成日报周报月报，批量替换格式",
        "category": "office",
        "keywords": ["excel", "表格", "合并", "拆分", "报表", "office"],
        "permissions": ["filesystem:read"],
        "level": "intermediate",
        "dependencies": ["openpyxl"],
    },
    "file_manager": {
        "class": "FileManagerSkill",
        "name": "文件管理器",
        "description": "文件管理：批量重命名、分类整理、搜索查找、权限管理",
        "category": "office",
        "keywords": ["文件", "重命名", "整理", "搜索", "office"],
        "permissions": ["filesystem:read", "filesystem:write"],
        "level": "beginner",
        "dependencies": [],
    },
    "email_processor": {
        "class": "EmailProcessorSkill",
        "name": "邮件处理",
        "description": "邮件处理：批量读取、分类过滤、自动回复、附件提取",
        "category": "office",
        "keywords": ["邮件", "email", "附件", "office"],
        "permissions": ["email"],
        "level": "intermediate",
        "dependencies": [],
    },
    "email_automation": {
        "class": "EmailAutomationSkill",
        "name": "邮件自动化",
        "description": "邮件自动化：定时发送、批量群发、邮件模板、跟踪提醒",
        "category": "office",
        "keywords": ["邮件", "自动化", "群发", "模板", "office"],
        "permissions": ["email"],
        "level": "intermediate",
        "dependencies": [],
    },
    "pdf_processor": {
        "class": "PDFProcessorSkill",
        "name": "PDF处理",
        "description": "PDF处理：合并拆分、提取文字、添加水印、格式转换",
        "category": "office",
        "keywords": ["pdf", "合并", "水印", "转换", "office"],
        "permissions": ["filesystem:read"],
        "level": "intermediate",
        "dependencies": ["PyPDF2"],
    },
    "spreadsheet_handler": {
        "class": "SpreadsheetHandlerSkill",
        "name": "表格处理器",
        "description": "表格处理：数据透视、公式计算、图表生成、条件格式",
        "category": "office",
        "keywords": ["表格", "透视", "公式", "图表", "office"],
        "permissions": ["filesystem:read"],
        "level": "advanced",
        "dependencies": ["openpyxl"],
    },
    "batch_file_processor": {
        "class": "BatchFileProcessorSkill",
        "name": "批量文件处理",
        "description": "批量文件：批量转换格式、压缩解压、批量重命名、格式统一",
        "category": "office",
        "keywords": ["批量", "文件", "转换", "压缩", "office"],
        "permissions": ["filesystem:read", "filesystem:write"],
        "level": "intermediate",
        "dependencies": [],
    },
    "contract_extractor": {
        "class": "ContractExtractorSkill",
        "name": "合同要素提取",
        "description": "合同提取：自动识别合同中的关键要素、甲乙方、金额、期限、违约条款",
        "category": "office",
        "keywords": ["合同", "提取", "要素", "office"],
        "permissions": ["filesystem:read"],
        "level": "advanced",
        "dependencies": [],
    },
    # ops
    "health_checker": {
        "class": "HealthCheckerSkill",
        "name": "系统健康检查",
        "description": "健康检查：检查磁盘空间、CPU、内存，异常自动告警",
        "category": "ops",
        "keywords": ["健康检查", "系统", "监控", "ops"],
        "permissions": [],
        "level": "intermediate",
        "dependencies": ["psutil"],
    },
    "process_monitor": {
        "class": "ProcessMonitorSkill",
        "name": "进程监控",
        "description": "进程监控：进程列表、CPU/内存占用、异常检测、自动重启",
        "category": "ops",
        "keywords": ["进程", "监控", "ops"],
        "permissions": [],
        "level": "intermediate",
        "dependencies": ["psutil"],
    },
    "backup": {
        "class": "BackupSkill",
        "name": "数据备份",
        "description": "数据备份：文件备份、定时备份、增量备份、压缩存储",
        "category": "ops",
        "keywords": ["备份", "数据", "ops"],
        "permissions": ["filesystem:read", "filesystem:write"],
        "level": "intermediate",
        "dependencies": [],
    },
    "backup_manager": {
        "class": "BackupManagerSkill",
        "name": "备份管理",
        "description": "备份管理：备份策略、备份恢复、备份验证、存储管理",
        "category": "ops",
        "keywords": ["备份", "管理", "恢复", "ops"],
        "permissions": ["filesystem:read", "filesystem:write"],
        "level": "advanced",
        "dependencies": [],
    },
    "log_viewer": {
        "class": "LogViewerSkill",
        "name": "日志查看器",
        "description": "日志查看：日志搜索、实时tail、关键词过滤、日志分析",
        "category": "ops",
        "keywords": ["日志", "log", "查看", "ops"],
        "permissions": ["filesystem:read"],
        "level": "beginner",
        "dependencies": [],
    },
    "log_cleaner": {
        "class": "LogCleanerSkill",
        "name": "日志清理",
        "description": "日志清理：过期日志清理、磁盘空间释放、日志归档",
        "category": "ops",
        "keywords": ["日志", "清理", "磁盘", "ops"],
        "permissions": ["filesystem:write"],
        "level": "beginner",
        "dependencies": [],
    },
    # marketing
    "wechat_group_monitor": {
        "class": "WeChatGroupMonitorSkill",
        "name": "微信群监控",
        "description": "微信群监控：关键词提醒、新消息通知、群活跃度统计",
        "category": "marketing",
        "keywords": ["微信", "群", "监控", "marketing"],
        "permissions": ["network"],
        "level": "intermediate",
        "dependencies": [],
    },
    "media_processor": {
        "class": "MediaProcessorSkill",
        "name": "媒体内容处理",
        "description": "媒体处理：图片压缩、视频转码、音频提取、格式转换",
        "category": "marketing",
        "keywords": ["媒体", "图片", "视频", "marketing"],
        "permissions": ["filesystem:read", "filesystem:write"],
        "level": "intermediate",
        "dependencies": [],
    },
    "customer_importer": {
        "class": "CustomerImporterSkill",
        "name": "客户数据导入",
        "description": "客户导入：批量导入客户数据、重复检测、数据验证",
        "category": "marketing",
        "keywords": ["客户", "导入", "数据", "marketing"],
        "permissions": ["filesystem:read", "database"],
        "level": "intermediate",
        "dependencies": [],
    },
    "competitor_monitor": {
        "class": "CompetitorMonitorSkill",
        "name": "竞品动态监控",
        "description": "竞品监控：竞争对手动态追踪、价格监控、新品监控",
        "category": "marketing",
        "keywords": ["竞品", "监控", "marketing"],
        "permissions": ["network"],
        "level": "advanced",
        "dependencies": [],
    },
    # management
    "attendance_processor": {
        "class": "AttendanceProcessorSkill",
        "name": "考勤处理",
        "description": "考勤处理：导入打卡记录自动算工时、迟到、加班，生成工资表基础数据",
        "category": "management",
        "keywords": ["考勤", "打卡", "工资", "management"],
        "permissions": ["filesystem:read", "database"],
        "level": "intermediate",
        "dependencies": ["openpyxl"],
    },
    "inventory_manager": {
        "class": "InventoryManagerSkill",
        "name": "库存管理",
        "description": "库存管理：库存查询、预警提醒、出入库记录、盘点",
        "category": "management",
        "keywords": ["库存", "管理", "management"],
        "permissions": ["database"],
        "level": "intermediate",
        "dependencies": [],
    },
    "order_sync": {
        "class": "OrderSyncSkill",
        "name": "订单同步",
        "description": "订单同步：多平台订单拉取、状态同步、异常告警",
        "category": "management",
        "keywords": ["订单", "同步", "management"],
        "permissions": ["network", "database"],
        "level": "advanced",
        "dependencies": [],
    },
    "meeting_notes_generator": {
        "class": "MeetingNotesGeneratorSkill",
        "name": "会议纪要生成",
        "description": "会议纪要：根据会议内容自动生成结构化会议纪要、待办事项",
        "category": "management",
        "keywords": ["会议", "纪要", "management"],
        "permissions": [],
        "level": "intermediate",
        "dependencies": [],
    },
    # security
    "security_scanner": {
        "class": "SecurityScannerSkill",
        "name": "安全扫描",
        "description": "安全扫描：代码安全扫描、敏感信息检测、漏洞检测",
        "category": "security",
        "keywords": ["安全", "扫描", "漏洞", "security"],
        "permissions": ["filesystem:read"],
        "level": "advanced",
        "dependencies": [],
    },
    # ai
    "nlp_task_generator": {
        "class": "NLPTaskGeneratorSkill",
        "name": "NLP任务生成器",
        "description": "NLP任务：文本分类、情感分析、实体识别、关键词提取",
        "category": "ai",
        "keywords": ["nlp", "自然语言", "分类", "ai"],
        "permissions": [],
        "level": "advanced",
        "dependencies": [],
    },
    "copywriter_ai": {
        "class": "CopywriterAISkill",
        "name": "AI文案生成",
        "description": "AI文案：广告语、朋友圈文案、产品介绍、邮件模板、报价单模板生成",
        "category": "ai",
        "keywords": ["ai", "文案", "生成", "ai"],
        "permissions": [],
        "level": "intermediate",
        "dependencies": [],
    },
    "ocr_processor": {
        "class": "OCRProcessorSkill",
        "name": "OCR文字识别",
        "description": "OCR识别：图片文字识别、PDF转文字、表格识别、批量识别",
        "category": "ai",
        "keywords": ["ocr", "识别", "文字", "ai"],
        "permissions": ["filesystem:read"],
        "level": "intermediate",
        "dependencies": ["pytesseract"],
    },
    "workflow_chain": {
        "class": "WorkflowChainSkill",
        "name": "工作流链式编排",
        "description": "工作流编排：多个技能链式执行、条件分支、循环处理",
        "category": "ai",
        "keywords": ["工作流", "编排", "链式", "ai"],
        "permissions": [],
        "level": "advanced",
        "dependencies": [],
    },
}


def make_plugin_id(name: str) -> str:
    return re.sub(r'[^a-z0-9_]', '_', name.lower().replace(' ', '_'))


def get_class_import_path(class_name: str) -> str:
    mapping = {
        "ExcelProcessorSkill": "wanclaw.backend.skills.office.excel_processor",
        "FileManagerSkill": "wanclaw.backend.skills.office.file_manager",
        "EmailProcessorSkill": "wanclaw.backend.skills.office.email_processor",
        "EmailAutomationSkill": "wanclaw.backend.skills.office.email_automation",
        "PDFProcessorSkill": "wanclaw.backend.skills.office.pdf_processor",
        "SpreadsheetHandlerSkill": "wanclaw.backend.skills.office.spreadsheet_handler",
        "BatchFileProcessorSkill": "wanclaw.backend.skills.office.batch_file_processor",
        "ContractExtractorSkill": "wanclaw.backend.skills.office.contract_extractor",
        "HealthCheckerSkill": "wanclaw.backend.skills.ops.health_checker",
        "ProcessMonitorSkill": "wanclaw.backend.skills.ops.process_monitor",
        "BackupSkill": "wanclaw.backend.skills.ops.backup",
        "BackupManagerSkill": "wanclaw.backend.skills.ops.backup_manager",
        "LogViewerSkill": "wanclaw.backend.skills.ops.log_viewer",
        "LogCleanerSkill": "wanclaw.backend.skills.ops.log_cleaner",
        "WeChatGroupMonitorSkill": "wanclaw.backend.skills.marketing.wechat_group_monitor",
        "MediaProcessorSkill": "wanclaw.backend.skills.marketing.media_processor",
        "CustomerImporterSkill": "wanclaw.backend.skills.marketing.customer_importer",
        "CompetitorMonitorSkill": "wanclaw.backend.skills.marketing.competitor_monitor",
        "AttendanceProcessorSkill": "wanclaw.backend.skills.management.attendance_processor",
        "InventoryManagerSkill": "wanclaw.backend.skills.management.inventory_manager",
        "OrderSyncSkill": "wanclaw.backend.skills.management.order_sync",
        "MeetingNotesGeneratorSkill": "wanclaw.backend.skills.management.meeting_notes_generator",
        "SecurityScannerSkill": "wanclaw.backend.skills.security.security_scanner",
        "NLPTaskGeneratorSkill": "wanclaw.backend.skills.ai.nlp_task_generator",
        "CopywriterAISkill": "wanclaw.backend.skills.ai.copywriter_ai",
        "OCRProcessorSkill": "wanclaw.backend.skills.ai.ocr_processor",
        "WorkflowChainSkill": "wanclaw.backend.skills.ai.workflow_chain",
    }
    return mapping.get(class_name, "")


def generate_plugin_json(skill_id: str, info: dict, version: str = "2.0.0") -> dict:
    category_map = {
        "office": "office", "ops": "ops", "marketing": "marketing",
        "management": "management", "security": "security", "ai": "ai",
    }
    return {
        "plugin_id": f"skill.{skill_id}",
        "plugin_name": info["name"],
        "plugin_type": "skill",
        "description": info["description"],
        "author": "WanClaw",
        "version": version,
        "category": category_map.get(info["category"], "ai"),
        "compatible_wanclaw_version": ">=2.0.0",
        "entry_file": "main.py",
        "permissions": info.get("permissions", []),
        "keywords": info.get("keywords", []),
        "level": info.get("level", "intermediate"),
        "is_official": True,
        "dependencies": info.get("dependencies", []),
        "marketplace": "clawhub",
        "download_count": 0,
        "rating": 5.0,
        "rating_count": 0,
        "review_status": "approved",
        "tags": ["官方", "内置", info["category"]],
    }


def generate_manifest_json(skill_id: str, info: dict) -> dict:
    return {
        "name": skill_id,
        "version": "2.0.0",
        "description": info["description"],
        "author": "WanClaw",
        "category": info["category"],
        "keywords": info.get("keywords", []),
        "entry_point": "main.py",
        "dependencies": info.get("dependencies", []),
        "permissions": info.get("permissions", []),
        "platforms": ["all"],
        "is_official": True,
        "wanclaw_version": ">=2.0.0",
    }


def generate_main_py(class_name: str, import_path: str) -> str:
    return f'''"""
{class_name} - WanClaw 官方技能插件
自动生成的插件适配器
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def run(**kwargs) -> Dict[str, Any]:
    """
    插件入口函数
    桥接到内置技能类
    """
    try:
        from wanclaw.backend.skills import BaseSkill, SkillResult, get_skill_manager

        manager = get_skill_manager()
        skill_instance = manager.get_skill("{class_name}")

        if not skill_instance:
            return {{
                "success": False,
                "error": "Skill not found: {class_name}",
                "message": "内置技能未注册"
            }}

        result = await skill_instance.execute(kwargs)

        return {{
            "success": result.success,
            "message": result.message,
            "data": result.data,
            "error": result.error,
            "execution_time": result.execution_time,
        }}
    except ImportError as e:
        logger.error(f"Failed to import skill system: {{e}}")
        return {{
            "success": False,
            "error": f"Import error: {{str(e)}}",
            "message": "无法加载技能系统"
        }}
    except Exception as e:
        logger.error(f"Skill execution failed: {{e}}")
        return {{
            "success": False,
            "error": str(e),
            "message": "技能执行失败"
        }}
'''


def generate_readme_md(skill_id: str, info: dict) -> str:
    level_names = {"beginner": "初级", "intermediate": "中级", "advanced": "高级"}
    category_names = {
        "office": "办公自动化", "ops": "运维管理", "marketing": "营销获客",
        "management": "管理运营", "security": "安全管理", "ai": "AI增强",
    }
    perms = "、".join(info.get("permissions", [])) if info.get("permissions") else "无需特殊权限"
    return f'''# {info["name"]}

## 插件信息

| 属性 | 值 |
|------|-----|
| 插件ID | skill.{skill_id} |
| 类型 | 官方内置技能 |
| 版本 | 2.0.0 |
| 分类 | {category_names.get(info["category"], info["category"])} |
| 难度 | {level_names.get(info.get("level", "intermediate"), "中级")} |
| 作者 | WanClaw |

## 功能描述

{info["description"]}

## 关键词

{" / ".join(info.get("keywords", []))}

## 权限说明

{perms}

## 使用方法

```python
# 通过插件系统调用
result = await plugin_manager.execute("skill.{skill_id}", {{"action": "xxx", ...}})
```

## 更新日志

### v2.0.0
- 转换为标准插件格式
- 支持通过 ClawHub 生态站分发

---
*此插件由 WanClaw 官方提供*
'''


def main():
    print(f"目标输出目录: {OUTPUT_DIR}")
    print(f"技能数量: {len(SKILL_DEFINITIONS)}")
    print("-" * 60)

    created = []
    skipped = []

    for skill_id, info in SKILL_DEFINITIONS.items():
        plugin_dir = OUTPUT_DIR / skill_id

        # 跳过已存在的
        if plugin_dir.exists():
            skipped.append(skill_id)
            continue

        plugin_dir.mkdir(parents=True, exist_ok=True)

        # 1. plugin.json (ClawHub生态站格式)
        plugin_json = generate_plugin_json(skill_id, info)
        with open(plugin_dir / "plugin.json", "w", encoding="utf-8") as f:
            json.dump(plugin_json, f, ensure_ascii=False, indent=2)

        # 2. manifest.json (WanClaw本地格式)
        manifest_json = generate_manifest_json(skill_id, info)
        with open(plugin_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest_json, f, ensure_ascii=False, indent=2)

        # 3. main.py
        import_path = get_class_import_path(info["class"])
        main_py = generate_main_py(info["class"], import_path)
        with open(plugin_dir / "main.py", "w", encoding="utf-8") as f:
            f.write(main_py)

        # 4. README.md
        readme_md = generate_readme_md(skill_id, info)
        with open(plugin_dir / "README.md", "w", encoding="utf-8") as f:
            f.write(readme_md)

        created.append(skill_id)
        print(f"  ✅ skill.{skill_id} - {info['name']}")

    print("-" * 60)
    print(f"创建: {len(created)} 个插件")
    if skipped:
        print(f"跳过: {len(skipped)} 个（已存在）")
    print(f"总计: {len(SKILL_DEFINITIONS)} 个内置技能已转换为插件")

    # 生成汇总 JSON
    summary = {
        "generated_at": datetime.now().isoformat(),
        "total": len(SKILL_DEFINITIONS),
        "created": created,
        "skipped": skipped,
        "plugins": {},
    }
    for skill_id, info in SKILL_DEFINITIONS.items():
        if skill_id in created:
            summary["plugins"][f"skill.{skill_id}"] = generate_plugin_json(skill_id, info)

    summary_path = OUTPUT_DIR / "_generated_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n汇总已保存到: {summary_path}")


if __name__ == "__main__":
    main()
