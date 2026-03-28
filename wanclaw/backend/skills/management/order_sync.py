"""
订单同步技能
电商订单/线下订单抓取，发货提醒、收款核对，未完成订单跟踪
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from wanclaw.backend.skills import BaseSkill, SkillResult, SkillCategory, SkillLevel


logger = logging.getLogger(__name__)


class OrderSyncSkill(BaseSkill):
    """订单同步技能"""
    
    def __init__(self):
        super().__init__()
        self.name = "OrderSync"
        self.description = "订单同步：电商/线下订单抓取，发货提醒、收款核对，未完成订单跟踪"
        self.category = SkillCategory.MANAGEMENT
        self.level = SkillLevel.INTERMEDIATE
        
        self.required_params = ["action"]
        
        self.optional_params = {
            "platform": str,
            "order_id": str,
            "status": str,
            "date_range": str,
            "notify": bool,
            "output_path": str
        }
    
    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        action = params.get("action", "").lower()
        
        try:
            if action == "sync":
                return await self._sync_orders(params)
            elif action == "ship_reminder":
                return await self._ship_reminder(params)
            elif action == "payment_check":
                return await self._payment_check(params)
            elif action == "track_pending":
                return await self._track_pending(params)
            elif action == "export":
                return await self._export_orders(params)
            else:
                return SkillResult(
                    success=False,
                    message=f"不支持的操作: {action}",
                    error=f"Unsupported action: {action}"
                )
        except Exception as e:
            logger.error(f"订单同步失败: {action} - {e}")
            return SkillResult(
                success=False,
                message=f"订单同步失败: {str(e)}",
                error=str(e)
            )
    
    async def _sync_orders(self, params: Dict[str, Any]) -> SkillResult:
        platform = params.get("platform", "all")
        date_range = params.get("date_range", "today")
        
        mock_orders = [
            {"order_id": "OD20240115001", "platform": "天猫", "customer": "张先生", "amount": 299.00, "status": "待发货", "items": 2, "created_at": "2024-01-15 10:30"},
            {"order_id": "OD20240115002", "platform": "京东", "customer": "李女士", "amount": 599.00, "status": "已发货", "items": 1, "created_at": "2024-01-15 11:45"},
            {"order_id": "OD20240115003", "platform": "线下", "customer": "王总", "amount": 1299.00, "status": "待付款", "items": 3, "created_at": "2024-01-15 14:20"},
            {"order_id": "OD20240115004", "platform": "天猫", "customer": "赵经理", "amount": 89.00, "status": "已完成", "items": 1, "created_at": "2024-01-15 16:00"}
        ]
        
        return SkillResult(
            success=True,
            message=f"订单同步完成，同步{len(mock_orders)}个订单",
            data={
                "platform": platform,
                "date_range": date_range,
                "orders": mock_orders,
                "total_orders": len(mock_orders),
                "total_amount": sum(o["amount"] for o in mock_orders),
                "sync_time": datetime.now().isoformat(),
                "note": "订单同步需要各平台API支持，当前返回模拟数据"
            }
        )
    
    async def _ship_reminder(self, params: Dict[str, Any]) -> SkillResult:
        notify = params.get("notify", True)
        
        mock_reminders = [
            {"order_id": "OD20240115001", "days_pending": 2, "customer": "张先生", "items": "产品A x2", "urgency": "high"},
            {"order_id": "OD20240114015", "days_pending": 3, "customer": "刘小姐", "items": "产品B x1", "urgency": "critical"},
            {"order_id": "OD20240114022", "days_pending": 3, "customer": "陈总", "items": "产品C x3", "urgency": "critical"}
        ]
        
        return SkillResult(
            success=True,
            message=f"发货提醒完成，{len(mock_reminders)}个订单待发货",
            data={
                "pending_shipments": mock_reminders,
                "notification_sent": notify,
                "critical_count": len([r for r in mock_reminders if r["urgency"] == "critical"]),
                "high_count": len([r for r in mock_reminders if r["urgency"] == "high"]),
                "note": "发货提醒功能，当前返回模拟数据"
            }
        )
    
    async def _payment_check(self, params: Dict[str, Any]) -> SkillResult:
        mock_unpaid = [
            {"order_id": "OD20240115003", "customer": "王总", "amount": 1299.00, "payment_method": "银行转账", "expected_date": "2024-01-15", "status": "未确认"},
            {"order_id": "OD20240114008", "customer": "周经理", "amount": 2599.00, "payment_method": "支付宝", "expected_date": "2024-01-14", "status": "逾期"},
            {"order_id": "OD20240112025", "customer": "吴总", "amount": 899.00, "payment_method": "微信", "expected_date": "2024-01-12", "status": "逾期"}
        ]
        
        return SkillResult(
            success=True,
            message=f"收款核对完成，{len(mock_unpaid)}个订单待收款",
            data={
                "unpaid_orders": mock_unpaid,
                "total_unpaid": sum(o["amount"] for o in mock_unpaid),
                "overdue_count": len([o for o in mock_unpaid if o["status"] == "逾期"]),
                "overdue_amount": sum(o["amount"] for o in mock_unpaid if o["status"] == "逾期"),
                "note": "收款核对功能，当前返回模拟数据"
            }
        )
    
    async def _track_pending(self, params: Dict[str, Any]) -> SkillResult:
        mock_pending = [
            {"order_id": "OD20240110005", "stage": "待确认", "days_in_stage": 5, "customer": "孙先生", "amount": 599.00, "last_action": "等待客户确认"},
            {"order_id": "OD20240108012", "stage": "待生产", "days_in_stage": 7, "customer": "郑总", "amount": 8999.00, "last_action": "等待生产排期"},
            {"order_id": "OD20240105018", "stage": "待发货", "days_in_stage": 10, "customer": "何经理", "amount": 1299.00, "last_action": "等待库存确认"},
            {"order_id": "OD20240102022", "stage": "待收货", "days_in_stage": 13, "customer": "冯小姐", "amount": 459.00, "last_action": "物流配送中"}
        ]
        
        return SkillResult(
            success=True,
            message=f"未完成订单跟踪完成，{len(mock_pending)}个订单待处理",
            data={
                "pending_orders": mock_pending,
                "stages_breakdown": {
                    "待确认": 1,
                    "待生产": 1,
                    "待发货": 1,
                    "待收货": 1
                },
                "stale_orders": len([p for p in mock_pending if p["days_in_stage"] > 7]),
                "note": "未完成订单跟踪功能，当前返回模拟数据"
            }
        )
    
    async def _export_orders(self, params: Dict[str, Any]) -> SkillResult:
        date_range = params.get("date_range", "last_30_days")
        output_path = params.get("output_path", "orders_export.xlsx")
        
        return SkillResult(
            success=True,
            message=f"订单导出完成",
            data={
                "output_file": output_path,
                "date_range": date_range,
                "orders_exported": 125,
                "export_format": "xlsx",
                "total_amount": 45890.00,
                "note": "订单导出需要openpyxl支持，当前返回模拟数据"
            }
        )
