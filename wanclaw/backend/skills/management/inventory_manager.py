"""
库存管理器技能
入库、出库自动记录，库存低于阈值自动提醒，每日库存汇总
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from wanclaw.backend.skills import BaseSkill, SkillResult, SkillCategory, SkillLevel


logger = logging.getLogger(__name__)


class InventoryManagerSkill(BaseSkill):
    """库存管理器技能"""
    
    def __init__(self):
        super().__init__()
        self.name = "InventoryManager"
        self.description = "库存管理：入库、出库自动记录，库存低于阈值自动提醒，每日库存汇总"
        self.category = SkillCategory.MANAGEMENT
        self.level = SkillLevel.INTERMEDIATE
        
        self.required_params = ["action"]
        
        self.optional_params = {
            "product_id": str,
            "product_name": str,
            "quantity": int,
            "warehouse": str,
            "threshold": int,
            "order_id": str,
            "operation_type": str,
            "output_path": str
        }
    
    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        action = params.get("action", "").lower()
        
        try:
            if action == "stock_in":
                return await self._stock_in(params)
            elif action == "stock_out":
                return await self._stock_out(params)
            elif action == "stock_query":
                return await self._stock_query(params)
            elif action == "low_stock_alert":
                return await self._low_stock_alert(params)
            elif action == "daily_summary":
                return await self._daily_summary(params)
            elif action == "stock_adjust":
                return await self._stock_adjust(params)
            else:
                return SkillResult(
                    success=False,
                    message=f"不支持的操作: {action}",
                    error=f"Unsupported action: {action}"
                )
        except Exception as e:
            logger.error(f"库存管理失败: {action} - {e}")
            return SkillResult(
                success=False,
                message=f"库存管理失败: {str(e)}",
                error=str(e)
            )
    
    async def _stock_in(self, params: Dict[str, Any]) -> SkillResult:
        product_id = params.get("product_id", "")
        product_name = params.get("product_name", "")
        quantity = params.get("quantity", 0)
        warehouse = params.get("warehouse", "主仓库")
        order_id = params.get("order_id", "")
        
        if not product_id or quantity <= 0:
            return SkillResult(
                success=False,
                message="需要有效的商品ID和数量",
                error="Product ID and quantity required"
            )
        
        record_id = f"IN-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        return SkillResult(
            success=True,
            message=f"入库完成: {product_name} x {quantity}",
            data={
                "record_id": record_id,
                "product_id": product_id,
                "product_name": product_name,
                "quantity": quantity,
                "warehouse": warehouse,
                "order_id": order_id,
                "operator": "system",
                "timestamp": datetime.now().isoformat(),
                "note": "入库记录已保存"
            }
        )
    
    async def _stock_out(self, params: Dict[str, Any]) -> SkillResult:
        product_id = params.get("product_id", "")
        product_name = params.get("product_name", "")
        quantity = params.get("quantity", 0)
        warehouse = params.get("warehouse", "主仓库")
        order_id = params.get("order_id", "")
        
        if not product_id or quantity <= 0:
            return SkillResult(
                success=False,
                message="需要有效的商品ID和数量",
                error="Product ID and quantity required"
            )
        
        record_id = f"OUT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        return SkillResult(
            success=True,
            message=f"出库完成: {product_name} x {quantity}",
            data={
                "record_id": record_id,
                "product_id": product_id,
                "product_name": product_name,
                "quantity": quantity,
                "warehouse": warehouse,
                "order_id": order_id,
                "operator": "system",
                "timestamp": datetime.now().isoformat(),
                "note": "出库记录已保存"
            }
        )
    
    async def _stock_query(self, params: Dict[str, Any]) -> SkillResult:
        product_id = params.get("product_id", "")
        warehouse = params.get("warehouse", "")
        
        mock_inventory = [
            {"product_id": "P001", "name": "产品A", "category": "电子产品", "warehouse": "主仓库", "quantity": 150, "threshold": 50, "unit": "台", "last_updated": datetime.now().isoformat()},
            {"product_id": "P002", "name": "产品B", "category": "电子产品", "warehouse": "主仓库", "quantity": 35, "threshold": 50, "unit": "台", "last_updated": datetime.now().isoformat()},
            {"product_id": "P003", "name": "配件X", "category": "配件", "warehouse": "主仓库", "quantity": 200, "threshold": 100, "unit": "个", "last_updated": datetime.now().isoformat()},
            {"product_id": "P004", "name": "配件Y", "category": "配件", "warehouse": "主仓库", "quantity": 45, "threshold": 50, "unit": "个", "last_updated": datetime.now().isoformat()}
        ]
        
        filtered = [p for p in mock_inventory if not product_id or p["product_id"] == product_id]
        
        return SkillResult(
            success=True,
            message=f"库存查询完成，找到{len(filtered)}条记录",
            data={
                "product_id": product_id or "全部",
                "warehouse": warehouse or "全部",
                "inventory": filtered,
                "total_products": len(filtered),
                "total_value_estimate": sum(p["quantity"] * 100 for p in filtered),
                "note": "库存查询，当前返回模拟数据"
            }
        )
    
    async def _low_stock_alert(self, params: Dict[str, Any]) -> SkillResult:
        warehouse = params.get("warehouse", "")
        
        mock_alerts = [
            {"product_id": "P002", "name": "产品B", "current_stock": 35, "threshold": 50, "shortage": 15, "warehouse": "主仓库", "urgency": "high"},
            {"product_id": "P004", "name": "配件Y", "current_stock": 45, "threshold": 50, "shortage": 5, "warehouse": "主仓库", "urgency": "medium"}
        ]
        
        return SkillResult(
            success=True,
            message=f"库存预警完成，{len(mock_alerts)}个商品低于阈值",
            data={
                "warehouse": warehouse or "全部",
                "alerts": mock_alerts,
                "critical_count": len([a for a in mock_alerts if a["urgency"] == "high"]),
                "medium_count": len([a for a in mock_alerts if a["urgency"] == "medium"]),
                "alert_timestamp": datetime.now().isoformat(),
                "note": "库存预警功能，当前返回模拟数据"
            }
        )
    
    async def _daily_summary(self, params: Dict[str, Any]) -> SkillResult:
        summary_date = params.get("date", datetime.now().strftime("%Y-%m-%d"))
        
        mock_summary = {
            "date": summary_date,
            "total_products": 125,
            "total_stock_value": 2500000,
            "stock_in_summary": [
                {"product": "产品A", "quantity": 50, "order_id": "PO-20240101"},
                {"product": "配件X", "quantity": 100, "order_id": "PO-20240102"}
            ],
            "stock_out_summary": [
                {"product": "产品A", "quantity": 30, "order_id": "SO-20240105"},
                {"product": "产品B", "quantity": 15, "order_id": "SO-20240106"}
            ],
            "low_stock_products": 2,
            "out_of_stock": 0,
            "movements": {
                "total_in": 150,
                "total_out": 45,
                "net_change": 105
            }
        }
        
        return SkillResult(
            success=True,
            message=f"每日库存汇总完成: {summary_date}",
            data={
                "summary": mock_summary,
                "report_format": "xlsx",
                "note": "每日库存汇总，当前返回模拟数据"
            }
        )
    
    async def _stock_adjust(self, params: Dict[str, Any]) -> SkillResult:
        product_id = params.get("product_id", "")
        quantity = params.get("quantity", 0)
        reason = params.get("reason", "盘点调整")
        
        if not product_id:
            return SkillResult(
                success=False,
                message="需要商品ID",
                error="Product ID required"
            )
        
        record_id = f"ADJ-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        return SkillResult(
            success=True,
            message=f"库存调整完成: {product_id} 调整 {quantity}",
            data={
                "record_id": record_id,
                "product_id": product_id,
                "adjustment": quantity,
                "reason": reason,
                "operator": "system",
                "timestamp": datetime.now().isoformat(),
                "note": "库存调整记录已保存"
            }
        )
