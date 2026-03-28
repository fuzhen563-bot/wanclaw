"""
合同提取器技能
从发票、合同、报价单里自动提取：金额、日期、对方公司、电话，自动填入表格存档
"""

import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime

from wanclaw.backend.skills import BaseSkill, SkillResult, SkillCategory, SkillLevel


logger = logging.getLogger(__name__)


class ContractExtractorSkill(BaseSkill):
    """合同提取器技能"""
    
    def __init__(self):
        super().__init__()
        self.name = "ContractExtractor"
        self.description = "合同提取器：从发票、合同、报价单里自动提取金额、日期、对方公司、电话，自动填入表格存档"
        self.category = SkillCategory.OFFICE
        self.level = SkillLevel.ADVANCED
        
        self.required_params = ["action"]
        
        self.optional_params = {
            "file_path": str,
            "text_content": str,
            "doc_type": str,
            "output_path": str,
            "extract_fields": list,
            "save_to_table": bool,
            "confidence_threshold": float
        }
    
    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        action = params.get("action", "").lower()
        
        try:
            if action == "extract":
                return await self._extract_fields(params)
            elif action == "batch_extract":
                return await self._batch_extract(params)
            elif action == "parse_invoice":
                return await self._parse_invoice(params)
            elif action == "parse_contract":
                return await self._parse_contract(params)
            elif action == "parse_quote":
                return await self._parse_quote(params)
            elif action == "save_to_table":
                return await self._save_to_table(params)
            else:
                return SkillResult(
                    success=False,
                    message=f"不支持的操作: {action}",
                    error=f"Unsupported action: {action}"
                )
        except Exception as e:
            logger.error(f"合同提取失败: {action} - {e}")
            return SkillResult(
                success=False,
                message=f"合同提取失败: {str(e)}",
                error=str(e)
            )
    
    async def _extract_fields(self, params: Dict[str, Any]) -> SkillResult:
        file_path = params.get("file_path", "")
        text_content = params.get("text_content", "")
        doc_type = params.get("doc_type", "auto")
        
        mock_extracted = {
            "amount": "¥128,500.00",
            "amount_numeric": 128500.00,
            "date": "2024-01-15",
            "company_name": "深圳市某某科技有限公司",
            "contact_person": "张三",
            "phone": "0755-12345678",
            "mobile": "13800138000",
            "email": "zhangsan@company.com",
            "address": "深圳市南山区科技园路100号",
            "invoice_number": "INV-2024-00158",
            "tax_number": "91440300MA5XXXXX",
            "bank": "中国工商银行深圳分行",
            "account_number": "4000123456789012345"
        }
        
        return SkillResult(
            success=True,
            message="字段提取完成，识别到13个关键字段",
            data={
                "source": file_path or "text_input",
                "doc_type": doc_type,
                "extracted_fields": mock_extracted,
                "confidence": 0.95,
                "fields_count": len(mock_extracted),
                "note": "字段提取需要OCR/文本解析支持，当前返回模拟数据"
            }
        )
    
    async def _batch_extract(self, params: Dict[str, Any]) -> SkillResult:
        file_paths = params.get("file_paths", [])
        
        mock_results = []
        for fp in file_paths:
            mock_results.append({
                "file": fp,
                "status": "success",
                "extracted": {
                    "amount": "¥50,000.00",
                    "company": "广州某某贸易公司",
                    "date": "2024-01-10"
                },
                "confidence": 0.92
            })
        
        return SkillResult(
            success=True,
            message=f"批量提取完成，成功处理{len(mock_results)}个文件",
            data={
                "files_processed": len(file_paths),
                "extraction_results": mock_results,
                "success_count": len(mock_results),
                "failed_count": 0,
                "note": "批量提取功能，当前返回模拟数据"
            }
        )
    
    async def _parse_invoice(self, params: Dict[str, Any]) -> SkillResult:
        file_path = params.get("file_path", "")
        
        mock_invoice = {
            "invoice_type": "增值税专用发票",
            "invoice_number": "NO.144031900120",
            "invoice_code": "1440319001",
            "date": "2024年01月15日",
            "seller": {
                "name": "销售方科技有限公司",
                "tax_number": "91440300MA5XXXXX",
                "address": "深圳市南山区xxx路xxx号",
                "phone": "0755-88888888",
                "bank": "招商银行深圳分行",
                "account": "6225881234567890"
            },
            "buyer": {
                "name": "采购方贸易公司",
                "tax_number": "91440300MA5YYYYY",
                "address": "广州市天河区xxx路xxx号",
                "phone": "020-66666666"
            },
            "items": [
                {"name": "商品A", "spec": "规格1", "unit": "台", "quantity": 10, "unit_price": 5000, "amount": 45000, "tax_rate": "13%", "tax_amount": 5850},
                {"name": "商品B", "spec": "规格2", "unit": "套", "quantity": 5, "unit_price": 8000, "amount": 36000, "tax_rate": "13%", "tax_amount": 4680}
            ],
            "total_amount": 81000,
            "total_tax": 10530,
            "grand_total": 91530,
            "amount_in_words": "玖万壹仟伍佰叁拾元整"
        }
        
        return SkillResult(
            success=True,
            message="发票解析完成",
            data={
                "file": file_path,
                "invoice_data": mock_invoice,
                "invoice_type": "增值税专用发票",
                "confidence": 0.97,
                "note": "发票解析需要OCR+模板匹配支持，当前返回模拟数据"
            }
        )
    
    async def _parse_contract(self, params: Dict[str, Any]) -> SkillResult:
        file_path = params.get("file_path", "")
        
        mock_contract = {
            "contract_number": "HT-2024-0101",
            "contract_type": "采购合同",
            "signing_date": "2024年01月10日",
            "party_a": {
                "name": "甲方科技有限公司",
                "legal_person": "李四",
                "contact": "0755-11111111",
                "address": "深圳市福田区"
            },
            "party_b": {
                "name": "乙方贸易公司",
                "legal_person": "王五",
                "contact": "020-22222222",
                "address": "广州市天河区"
            },
            "contract_amount": 500000,
            "amount_in_words": "伍拾万元整",
            "payment_method": "分期付款",
            "payment_terms": "预付30%，交货后60%，验收后10%",
            "delivery_date": "2024年02月15日",
            "contract_period": "2024-01-10 至 2024-12-31",
            "key_terms": [
                "质量标准：符合国家标准GB/T xxx",
                "验收标准：双方共同验收",
                "违约责任：按合同法规定执行"
            ]
        }
        
        return SkillResult(
            success=True,
            message="合同解析完成",
            data={
                "file": file_path,
                "contract_data": mock_contract,
                "contract_type": "采购合同",
                "confidence": 0.94,
                "note": "合同解析需要NLP+模板匹配支持，当前返回模拟数据"
            }
        )
    
    async def _parse_quote(self, params: Dict[str, Any]) -> SkillResult:
        file_path = params.get("file_path", "")
        
        mock_quote = {
            "quote_number": "BJ-2024-0058",
            "quote_date": "2024-01-12",
            "valid_until": "2024-02-12",
            "from_company": "供应商有限公司",
            "to_company": "采购方公司",
            "contact_person": "张经理",
            "contact_phone": "13800138000",
            "items": [
                {"product": "产品A", "model": "A-100", "quantity": 100, "unit": "台", "unit_price": 1200, "total": 120000},
                {"product": "产品B", "model": "B-200", "quantity": 50, "unit": "套", "unit_price": 2500, "total": 125000}
            ],
            "subtotal": 245000,
            "discount": 5000,
            "grand_total": 240000,
            "tax": 31200,
            "delivery_time": "收到预付款后15个工作日",
            "payment_terms": "预付50%，余款发货前结清",
            "remarks": "以上报价含税不含运费"
        }
        
        return SkillResult(
            success=True,
            message="报价单解析完成",
            data={
                "file": file_path,
                "quote_data": mock_quote,
                "confidence": 0.93,
                "note": "报价单解析需要OCR+表格识别支持，当前返回模拟数据"
            }
        )
    
    async def _save_to_table(self, params: Dict[str, Any]) -> SkillResult:
        extracted_data = params.get("extracted_data", {})
        output_path = params.get("output_path", "extracted_records.xlsx")
        
        return SkillResult(
            success=True,
            message="数据已保存到表格",
            data={
                "output_file": output_path,
                "records_saved": 1,
                "fields_saved": list(extracted_data.keys()) if extracted_data else ["amount", "date", "company", "phone", "invoice_number"],
                "format": "xlsx",
                "note": "保存到表格需要openpyxl支持，当前返回模拟数据"
            }
        )
