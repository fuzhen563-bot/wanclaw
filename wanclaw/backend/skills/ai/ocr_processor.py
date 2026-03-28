"""
OCR处理技能
拍照/截图转文字，名片自动识别录入
"""

import os
import logging
import base64
from typing import Dict, List, Optional, Any
from datetime import datetime

from wanclaw.backend.skills import BaseSkill, SkillResult, SkillCategory, SkillLevel


logger = logging.getLogger(__name__)


class OCRProcessorSkill(BaseSkill):
    """OCR处理技能"""
    
    def __init__(self):
        super().__init__()
        self.name = "OCRProcessor"
        self.description = "OCR处理：拍照/截图转文字，名片自动识别录入"
        self.category = SkillCategory.AI
        self.level = SkillLevel.INTERMEDIATE
        
        self.required_params = ["action"]
        
        self.optional_params = {
            "image_path": str,
            "image_data": str,
            "ocr_type": str,
            "language": str,
            "save_to": str,
            "enhance": bool
        }
    
    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        action = params.get("action", "").lower()
        
        try:
            if action == "recognize":
                return await self._recognize_text(params)
            elif action == "business_card":
                return await self._recognize_business_card(params)
            elif action == "receipt":
                return await self._recognize_receipt(params)
            elif action == "document":
                return await self._recognize_document(params)
            else:
                return SkillResult(
                    success=False,
                    message=f"不支持的操作: {action}",
                    error=f"Unsupported action: {action}"
                )
        except Exception as e:
            logger.error(f"OCR处理失败: {action} - {e}")
            return SkillResult(
                success=False,
                message=f"OCR处理失败: {str(e)}",
                error=str(e)
            )
    
    async def _recognize_text(self, params: Dict[str, Any]) -> SkillResult:
        image_path = params.get("image_path", "")
        image_data = params.get("image_data", "")
        language = params.get("language", "zh-CN")
        enhance = params.get("enhance", True)
        
        if not image_path and not image_data:
            return SkillResult(
                success=False,
                message="需要图片路径或图片数据",
                error="Image path or data required"
            )
        
        mock_text = """会议纪要 - 2024年1月15日

与会人员：张三、李四、王五、赵六

议题一：Q1产品规划
讨论了Q1季度的产品路线图，重点包括移动端优化和国际化拓展。
决定：2月底前完成移动端2.0版本开发。

议题二：市场推广预算
赵六提出了增加市场推广预算的方案。
决定：预算申请提交下周管理层会议审批。

议题三：团队建设
讨论了增加两名技术人员的招聘计划。
决定：HR启动招聘流程，目标2月底前到岗。

下一步行动：
• 李四 - 技术方案细化（1/20前）
• 王五 - 市场方案制定（1/22前）
• 赵六 - 预算方案完善（1/18前）"""
        
        mock_blocks = [
            {"text": "会议纪要 - 2024年1月15日", "bbox": [10, 10, 200, 30], "confidence": 0.98},
            {"text": "与会人员：张三、李四、王五、赵六", "bbox": [10, 35, 300, 55], "confidence": 0.97},
            {"text": "议题一：Q1产品规划", "bbox": [10, 65, 200, 85], "confidence": 0.99}
        ]
        
        return SkillResult(
            success=True,
            message="文字识别完成",
            data={
                "source": image_path or "image_data",
                "recognized_text": mock_text,
                "text_blocks": mock_blocks,
                "language": language,
                "enhance_applied": enhance,
                "confidence": 0.95,
                "word_count": len(mock_text),
                "note": "OCR识别需要pytesseract或百度OCR API支持，当前返回模拟数据"
            }
        )
    
    async def _recognize_business_card(self, params: Dict[str, Any]) -> SkillResult:
        image_path = params.get("image_path", "")
        save_to = params.get("save_to", "")
        
        if not image_path:
            return SkillResult(
                success=False,
                message="需要图片路径",
                error="Image path required"
            )
        
        mock_contact = {
            "name": "张经理",
            "title": "销售总监",
            "company": "科技有限公司",
            "department": "销售部",
            "phone": "0755-12345678",
            "mobile": "13800138000",
            "email": "zhang@tech-company.com",
            "website": "www.tech-company.com",
            "address": "深圳市南山区科技园路100号"
        }
        
        return SkillResult(
            success=True,
            message="名片识别完成",
            data={
                "image_path": image_path,
                "contact": mock_contact,
                "confidence": 0.93,
                "saved_to": save_to or "未指定",
                "fields_extracted": list(mock_contact.keys()),
                "note": "名片识别需要OCR+名片模板匹配支持，当前返回模拟数据"
            }
        )
    
    async def _recognize_receipt(self, params: Dict[str, Any]) -> SkillResult:
        image_path = params.get("image_path", "")
        
        if not image_path:
            return SkillResult(
                success=False,
                message="需要图片路径",
                error="Image path required"
            )
        
        mock_receipt = {
            "merchant_name": "某某超市",
            "merchant_address": "深圳市福田区华强北路100号",
            "receipt_number": "SL202401150001",
            "date": "2024-01-15 14:32:18",
            "items": [
                {"name": "矿泉水", "quantity": 2, "price": 3.00, "total": 6.00},
                {"name": "方便面", "quantity": 1, "price": 5.50, "total": 5.50},
                {"name": "面包", "quantity": 1, "price": 8.00, "total": 8.00}
            ],
            "subtotal": 19.50,
            "tax": 1.95,
            "total": 21.45,
            "payment_method": "微信支付",
            "cashier": "收银员01"
        }
        
        return SkillResult(
            success=True,
            message="收据识别完成",
            data={
                "image_path": image_path,
                "receipt": mock_receipt,
                "confidence": 0.91,
                "total_amount": mock_receipt["total"],
                "items_count": len(mock_receipt["items"]),
                "note": "收据识别需要OCR+表格识别支持，当前返回模拟数据"
            }
        )
    
    async def _recognize_document(self, params: Dict[str, Any]) -> SkillResult:
        image_path = params.get("image_path", "")
        ocr_type = params.get("ocr_type", "mixed")
        
        if not image_path:
            return SkillResult(
                success=False,
                message="需要图片路径",
                error="Image path required"
            )
        
        mock_doc = {
            "document_type": "合同",
            "key_fields": {
                "甲方": "科技有限公司",
                "乙方": "贸易有限公司",
                "合同金额": "人民币伍拾万元整（¥500,000）",
                "签订日期": "2024年1月10日",
                "合同编号": "HT-2024-0101"
            },
            "full_text": """合同
合同编号：HT-2024-0101

甲方（出卖人）：科技有限公司
地址：深圳市南山区科技园路100号

乙方（买受人）：贸易有限公司
地址：广州市天河区天河路200号

第一条 合同标的
甲方向乙方出售以下产品：...

第二条 合同金额
合同总金额为人民币伍拾万元整（¥500,000）。

第三条 付款方式
自本合同签订之日起5个工作日内，乙方向甲方支付合同总金额的30%作为预付款。
""",
            "tables": [
                {"headers": ["产品名称", "规格", "数量", "单价", "金额"], "rows": [["产品A", "规格1", "100", "2000", "200000"]]}
            ]
        }
        
        return SkillResult(
            success=True,
            message="文档识别完成",
            data={
                "image_path": image_path,
                "document": mock_doc,
                "ocr_type": ocr_type,
                "confidence": 0.89,
                "note": "文档识别需要OCR+文档分析支持，当前返回模拟数据"
            }
        )
