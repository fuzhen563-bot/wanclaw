"""
NLP任务生成技能
自然语言任务生成（"帮我整理本周销售数据"→自动调用对应技能）
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from wanclaw.backend.skills import BaseSkill, SkillResult, SkillCategory, SkillLevel


logger = logging.getLogger(__name__)


class NLPTaskGeneratorSkill(BaseSkill):
    """NLP任务生成技能"""
    
    def __init__(self):
        super().__init__()
        self.name = "NLPTaskGenerator"
        self.description = "NLP任务生成：自然语言任务生成，自动调用对应技能"
        self.category = SkillCategory.AI
        self.level = SkillLevel.ADVANCED
        
        self.required_params = ["action"]
        
        self.optional_params = {
            "query": str,
            "context": dict,
            "language": str,
            "confidence_threshold": float
        }
    
    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        action = params.get("action", "").lower()
        
        try:
            if action == "parse":
                return await self._parse_natural_language(params)
            elif action == "route":
                return await self._route_task(params)
            elif action == "chain":
                return await self._create_task_chain(params)
            else:
                return SkillResult(
                    success=False,
                    message=f"不支持的操作: {action}",
                    error=f"Unsupported action: {action}"
                )
        except Exception as e:
            logger.error(f"NLP任务生成失败: {action} - {e}")
            return SkillResult(
                success=False,
                message=f"NLP任务生成失败: {str(e)}",
                error=str(e)
            )
    
    async def _parse_natural_language(self, params: Dict[str, Any]) -> SkillResult:
        query = params.get("query", "")
        
        if not query:
            return SkillResult(
                success=False,
                message="需要查询文本",
                error="Query required"
            )
        
        skill_mapping = {
            "销售": ["SpreadsheetHandler", "ExcelProcessor"],
            "整理": ["FileManager", "BatchFileProcessor"],
            "备份": ["Backup", "BackupManager"],
            "监控": ["ProcessMonitor", "HealthChecker"],
            "日志": ["LogViewer", "LogCleaner"],
            "报告": ["ExcelProcessor", "MeetingNotesGenerator"],
            "邮件": ["EmailProcessor", "EmailAutomation"],
            "客户": ["CustomerImporter"],
            "考勤": ["AttendanceProcessor"],
            "库存": ["InventoryManager"],
            "订单": ["OrderSync"],
            "安全": ["SecurityScanner"]
        }
        
        detected_skills = []
        for keyword, skills in skill_mapping.items():
            if keyword in query:
                detected_skills.extend(skills)
        
        detected_skills = list(set(detected_skills))
        
        mock_parsed = {
            "original_query": query,
            "intent": self._detect_intent(query),
            "entities": self._extract_entities(query),
            "parameters": self._extract_parameters(query),
            "suggested_skills": detected_skills,
            "confidence": 0.92 if detected_skills else 0.65,
            "language": "zh-CN",
            "alternatives": self._generate_alternatives(query) if not detected_skills else []
        }
        
        return SkillResult(
            success=True,
            message=f"自然语言解析完成，识别到{len(detected_skills)}个可能技能",
            data={
                "parsed": mock_parsed,
                "query": query,
                "note": "自然语言解析需要NLP模型支持，当前返回模拟数据"
            }
        )
    
    async def _route_task(self, params: Dict[str, Any]) -> SkillResult:
        query = params.get("query", "")
        
        if not query:
            return SkillResult(
                success=False,
                message="需要查询文本",
                error="Query required"
            )
        
        mock_route = {
            "skill_name": "ExcelProcessor",
            "action": "report",
            "params": {
                "report_type": "weekly",
                "period": "本周",
                "template": "sales_summary"
            },
            "execution_plan": {
                "step": 1,
                "skill": "ExcelProcessor",
                "action": "report",
                "params": {"report_type": "weekly"}
            },
            "confidence": 0.95
        }
        
        return SkillResult(
            success=True,
            message="任务路由完成",
            data={
                "route": mock_route,
                "query": query,
                "skill_name": mock_route["skill_name"],
                "note": "任务路由需要NLP模型支持，当前返回模拟数据"
            }
        )
    
    async def _create_task_chain(self, params: Dict[str, Any]) -> SkillResult:
        query = params.get("query", "帮我备份数据然后发邮件")
        
        mock_chain = {
            "steps": [
                {"step": 1, "skill": "Backup", "action": "create", "params": {"source_path": "/data", "backup_path": "/backup"}, "depends_on": None},
                {"step": 2, "skill": "EmailAutomation", "action": "batch_send", "params": {"recipients": ["admin@company.com"], "subject": "备份完成通知"}, "depends_on": 1}
            ],
            "total_steps": 2,
            "estimated_time_seconds": 120,
            "can_parallelize": False
        }
        
        return SkillResult(
            success=True,
            message=f"任务链创建完成，共{len(mock_chain['steps'])}步",
            data={
                "chain": mock_chain,
                "query": query,
                "note": "任务链创建需要NLP模型支持，当前返回模拟数据"
            }
        )
    
    def _detect_intent(self, query: str) -> str:
        intent_keywords = {
            "生成": "generate",
            "整理": "organize",
            "分析": "analyze",
            "备份": "backup",
            "发送": "send",
            "查询": "query",
            "监控": "monitor",
            "检查": "check",
            "提取": "extract",
            "转换": "convert"
        }
        for keyword, intent in intent_keywords.items():
            if keyword in query:
                return intent
        return "unknown"
    
    def _extract_entities(self, query: str) -> List[Dict[str, Any]]:
        entities = []
        if "本周" in query or "本周" in query:
            entities.append({"type": "time", "value": "本周", "normalized": "current_week"})
        if "销售" in query:
            entities.append({"type": "topic", "value": "销售", "normalized": "sales"})
        if "数据" in query:
            entities.append({"type": "data_type", "value": "数据", "normalized": "data"})
        return entities
    
    def _extract_parameters(self, query: str) -> Dict[str, Any]:
        params = {}
        if "本周" in query:
            params["period"] = "本周"
        if "销售" in query:
            params["report_type"] = "销售报告"
        if "日报" in query:
            params["report_type"] = "daily"
        if "周报" in query:
            params["report_type"] = "weekly"
        if "月报" in query:
            params["report_type"] = "monthly"
        return params
    
    def _generate_alternatives(self, query: str) -> List[str]:
        return [
            f"是否要搜索'{query}'相关文件？",
            f"是否要监控系统'{query}'相关进程？",
            f"是否要查看'{query}'相关日志？"
        ]
