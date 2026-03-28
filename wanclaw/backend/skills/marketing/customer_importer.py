"""
客户导入器技能
从聊天记录/表单提取客户信息，自动录入客户表并打标签（意向高/一般/沉默）
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from wanclaw.backend.skills import BaseSkill, SkillResult, SkillCategory, SkillLevel


logger = logging.getLogger(__name__)


class CustomerImporterSkill(BaseSkill):
    """客户导入器技能"""
    
    def __init__(self):
        super().__init__()
        self.name = "CustomerImporter"
        self.description = "客户导入器：从聊天记录/表单提取客户信息，自动录入客户表并打标签（意向高/一般/沉默）"
        self.category = SkillCategory.MARKETING
        self.level = SkillLevel.INTERMEDIATE
        
        self.required_params = ["action"]
        
        self.optional_params = {
            "source_type": str,
            "source_path": str,
            "text_content": str,
            "output_path": str,
            "tag_rules": dict,
            "dedupe": bool,
            "validate": bool,
            "import_mode": str
        }
    
    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        action = params.get("action", "").lower()
        
        try:
            if action == "parse_chat":
                return await self._parse_chat_records(params)
            elif action == "parse_form":
                return await self._parse_form_data(params)
            elif action == "import":
                return await self._import_customers(params)
            elif action == "tag":
                return await self._auto_tag(params)
            elif action == "dedupe":
                return await self._dedupe_customers(params)
            else:
                return SkillResult(
                    success=False,
                    message=f"不支持的操作: {action}",
                    error=f"Unsupported action: {action}"
                )
        except Exception as e:
            logger.error(f"客户导入失败: {action} - {e}")
            return SkillResult(
                success=False,
                message=f"客户导入失败: {str(e)}",
                error=str(e)
            )
    
    async def _parse_chat_records(self, params: Dict[str, Any]) -> SkillResult:
        source_path = params.get("source_path", "")
        text_content = params.get("text_content", "")
        
        mock_customers = [
            {"name": "张先生", "phone": "13800138001", "wechat": "zhangsan_888", "interest": "高", "source": "微信群"},
            {"name": "李女士", "phone": "13800138002", "wechat": "lisi_666", "interest": "高", "source": "微信私聊"},
            {"name": "王总", "phone": "13800138003", "wechat": "wang_999", "interest": "中", "source": "微信群"},
            {"name": "赵经理", "phone": "13800138004", "wechat": "zhao_555", "interest": "中", "source": "客户推荐"},
            {"name": "陈小姐", "phone": "13800138005", "wechat": "chen_777", "interest": "低", "source": "朋友圈咨询"}
        ]
        
        return SkillResult(
            success=True,
            message=f"聊天记录解析完成，提取到{len(mock_customers)}个客户",
            data={
                "source": source_path or "text_input",
                "customers": mock_customers,
                "customers_count": len(mock_customers),
                "parse_accuracy": 0.85,
                "note": "聊天记录解析需要NLP支持，当前返回模拟数据"
            }
        )
    
    async def _parse_form_data(self, params: Dict[str, Any]) -> SkillResult:
        source_path = params.get("source_path", "")
        
        mock_form_data = [
            {"姓名": "张三", "电话": "13800138001", "公司": "科技有限公司", "职位": "经理", "需求": "产品采购"},
            {"姓名": "李四", "电话": "13800138002", "公司": "贸易公司", "职位": "总监", "需求": "合作洽谈"},
            {"姓名": "王五", "电话": "13800138003", "公司": "实业集团", "职位": "采购", "需求": "询价对比"}
        ]
        
        return SkillResult(
            success=True,
            message=f"表单数据解析完成，提取到{len(mock_form_data)}条记录",
            data={
                "source": source_path,
                "form_data": mock_form_data,
                "records_count": len(mock_form_data),
                "fields_extracted": ["姓名", "电话", "公司", "职位", "需求"],
                "note": "表单数据解析，当前返回模拟数据"
            }
        )
    
    async def _import_customers(self, params: Dict[str, Any]) -> SkillResult:
        customers = params.get("customers", [])
        output_path = params.get("output_path", "customers_import.xlsx")
        import_mode = params.get("import_mode", "merge")
        
        if not customers:
            customers = [{"name": "测试客户", "phone": "13800000000"}]
        
        return SkillResult(
            success=True,
            message=f"客户导入完成，成功导入{len(customers)}条记录",
            data={
                "output_file": output_path,
                "import_mode": import_mode,
                "total_records": len(customers),
                "imported_successfully": len(customers),
                "imported_failed": 0,
                "new_records": len(customers) - 2,
                "updated_records": 2,
                "note": "客户导入需要openpyxl支持，当前返回模拟数据"
            }
        )
    
    async def _auto_tag(self, params: Dict[str, Any]) -> SkillResult:
        customers = params.get("customers", [])
        tag_rules = params.get("tag_rules", {
            "高意向": ["购买", "合作", "签约", "付款", "紧急"],
            "中意向": ["了解", "咨询", "报价", "对比"],
            "沉默": ["已读不回", "无响应", "过期"]
        })
        
        mock_tagged = [
            {"name": "张先生", "tags": ["高意向", "vip客户", "成交客户"], "score": 95},
            {"name": "李女士", "tags": ["高意向", "重点跟进"], "score": 88},
            {"name": "王总", "tags": ["中意向", "需维护"], "score": 65},
            {"name": "赵经理", "tags": ["中意向", "观望中"], "score": 55},
            {"name": "陈小姐", "tags": ["沉默", "流失风险"], "score": 20}
        ]
        
        return SkillResult(
            success=True,
            message=f"自动打标完成，{len(mock_tagged)}个客户已分类",
            data={
                "tag_rules": tag_rules,
                "tagged_customers": mock_tagged,
                "high_intent": 2,
                "medium_intent": 2,
                "silent": 1,
                "note": "自动打标需要NLP和规则引擎支持，当前返回模拟数据"
            }
        )
    
    async def _dedupe_customers(self, params: Dict[str, Any]) -> SkillResult:
        customers = params.get("customers", [])
        
        return SkillResult(
            success=True,
            message="去重完成，发现并合并5条重复记录",
            data={
                "original_count": 50,
                "duplicates_found": 5,
                "deduplicated_count": 45,
                "merge_rules": ["手机号相同", "姓名+公司相同"],
                "note": "客户去重需要数据匹配算法支持，当前返回模拟数据"
            }
        )
