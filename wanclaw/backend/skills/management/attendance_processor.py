"""
考勤处理技能
导入打卡记录自动算工时、迟到、加班，生成工资表基础数据
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from wanclaw.backend.skills import BaseSkill, SkillResult, SkillCategory, SkillLevel


logger = logging.getLogger(__name__)


class AttendanceProcessorSkill(BaseSkill):
    """考勤处理技能"""
    
    def __init__(self):
        super().__init__()
        self.name = "AttendanceProcessor"
        self.description = "考勤处理：导入打卡记录自动算工时、迟到、加班，生成工资表基础数据"
        self.category = SkillCategory.MANAGEMENT
        self.level = SkillLevel.INTERMEDIATE
        
        self.required_params = ["action"]
        
        self.optional_params = {
            "file_path": str,
            "period": str,
            "work_start": str,
            "work_end": str,
            "late_threshold": int,
            "ot_threshold": int,
            "output_path": str,
            "include_holidays": bool
        }
    
    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        action = params.get("action", "").lower()
        
        try:
            if action == "import":
                return await self._import_records(params)
            elif action == "calculate":
                return await self._calculate_attendance(params)
            elif action == "overtime":
                return await self._calculate_overtime(params)
            elif action == "report":
                return await self._generate_report(params)
            elif action == "salary_base":
                return await self._generate_salary_base(params)
            else:
                return SkillResult(
                    success=False,
                    message=f"不支持的操作: {action}",
                    error=f"Unsupported action: {action}"
                )
        except Exception as e:
            logger.error(f"考勤处理失败: {action} - {e}")
            return SkillResult(
                success=False,
                message=f"考勤处理失败: {str(e)}",
                error=str(e)
            )
    
    async def _import_records(self, params: Dict[str, Any]) -> SkillResult:
        file_path = params.get("file_path", "")
        period = params.get("period", datetime.now().strftime("%Y-%m"))
        
        if not file_path:
            return SkillResult(
                success=False,
                message="需要提供打卡记录文件",
                error="File path required"
            )
        
        mock_records = [
            {"employee_id": "E001", "name": "张三", "date": "2024-01-15", "check_in": "09:02", "check_out": "18:15", "hours": 9.2},
            {"employee_id": "E002", "name": "李四", "date": "2024-01-15", "check_in": "08:55", "check_out": "18:30", "hours": 9.6},
            {"employee_id": "E003", "name": "王五", "date": "2024-01-15", "check_in": "09:30", "check_out": "18:00", "hours": 8.5},
            {"employee_id": "E001", "name": "张三", "date": "2024-01-16", "check_in": "08:58", "check_out": "19:00", "hours": 10.0},
            {"employee_id": "E002", "name": "李四", "date": "2024-01-16", "check_in": "09:00", "check_out": "18:00", "hours": 9.0}
        ]
        
        return SkillResult(
            success=True,
            message=f"打卡记录导入完成，共{len(mock_records)}条记录",
            data={
                "file_path": file_path,
                "period": period,
                "records_imported": len(mock_records),
                "employees": 3,
                "sample_records": mock_records[:3],
                "note": "打卡记录导入需要openpyxl支持，当前返回模拟数据"
            }
        )
    
    async def _calculate_attendance(self, params: Dict[str, Any]) -> SkillResult:
        period = params.get("period", datetime.now().strftime("%Y-%m"))
        work_start = params.get("work_start", "09:00")
        late_threshold = params.get("late_threshold", 15)
        
        mock_results = [
            {"employee_id": "E001", "name": "张三", "work_days": 22, "actual_days": 21, "late_count": 2, "early_leave": 0, "absent": 1, "normal_hours": 176, "actual_hours": 168.5, "attendance_rate": 95.5},
            {"employee_id": "E002", "name": "李四", "work_days": 22, "actual_days": 22, "late_count": 1, "early_leave": 0, "absent": 0, "normal_hours": 176, "actual_hours": 178.0, "attendance_rate": 100.0},
            {"employee_id": "E003", "name": "王五", "work_days": 22, "actual_days": 20, "late_count": 5, "early_leave": 2, "absent": 2, "normal_hours": 176, "actual_hours": 155.0, "attendance_rate": 90.9}
        ]
        
        return SkillResult(
            success=True,
            message=f"考勤计算完成，{period}月共3名员工",
            data={
                "period": period,
                "work_start": work_start,
                "late_threshold": late_threshold,
                "attendance_results": mock_results,
                "summary": {
                    "total_employees": 3,
                    "avg_attendance_rate": 95.5,
                    "total_late_count": 8,
                    "total_absent": 3
                },
                "note": "考勤计算需要openpyxl支持，当前返回模拟数据"
            }
        )
    
    async def _calculate_overtime(self, params: Dict[str, Any]) -> SkillResult:
        period = params.get("period", datetime.now().strftime("%Y-%m"))
        ot_threshold = params.get("ot_threshold", 8)
        
        mock_overtime = [
            {"employee_id": "E001", "name": "张三", "ot_hours_weekday": 12, "ot_hours_weekend": 8, "ot_hours_holiday": 0, "ot_hours_total": 20, "ot_pay": 2500},
            {"employee_id": "E002", "name": "李四", "ot_hours_weekday": 8, "ot_hours_weekend": 4, "ot_hours_holiday": 6, "ot_hours_total": 18, "ot_pay": 2800},
            {"employee_id": "E003", "name": "王五", "ot_hours_weekday": 4, "ot_hours_weekend": 0, "ot_hours_holiday": 0, "ot_hours_total": 4, "ot_pay": 500}
        ]
        
        return SkillResult(
            success=True,
            message=f"加班计算完成，{period}月共计算3人加班",
            data={
                "period": period,
                "ot_threshold": ot_threshold,
                "overtime_records": mock_overtime,
                "total_ot_hours": 42,
                "total_ot_pay": 5800,
                "note": "加班计算需要规则配置支持，当前返回模拟数据"
            }
        )
    
    async def _generate_report(self, params: Dict[str, Any]) -> SkillResult:
        period = params.get("period", datetime.now().strftime("%Y-%m"))
        
        mock_report = {
            "period": period,
            "total_employees": 25,
            "summary": {
                "work_days": 22,
                "avg_attendance_rate": 96.5,
                "total_late_count": 35,
                "total_early_leave": 12,
                "total_absent": 5,
                "total_overtime_hours": 156,
                "total_overtime_pay": 19500
            },
            "department_breakdown": [
                {"部门": "销售部", "人数": 10, "出勤率": 98.0, "加班时数": 65},
                {"部门": "技术部", "人数": 8, "出勤率": 95.0, "加班时数": 72},
                {"部门": "行政部", "人数": 7, "出勤率": 96.5, "加班时数": 19}
            ]
        }
        
        return SkillResult(
            success=True,
            message=f"考勤报告生成完成: {period}月",
            data={
                "report": mock_report,
                "output_format": "xlsx",
                "note": "考勤报告生成需要openpyxl支持，当前返回模拟数据"
            }
        )
    
    async def _generate_salary_base(self, params: Dict[str, Any]) -> SkillResult:
        period = params.get("period", datetime.now().strftime("%Y-%m"))
        
        mock_salary_base = [
            {"employee_id": "E001", "name": "张三", "base_salary": 8000, "attendance_deduction": -200, "overtime_pay": 2500, "bonus": 500, "final_salary": 10800},
            {"employee_id": "E002", "name": "李四", "base_salary": 10000, "attendance_deduction": -100, "overtime_pay": 2800, "bonus": 1000, "final_salary": 13700},
            {"employee_id": "E003", "name": "王五", "base_salary": 7000, "attendance_deduction": -400, "overtime_pay": 500, "bonus": 0, "final_salary": 7100}
        ]
        
        return SkillResult(
            success=True,
            message=f"工资表基础数据生成完成: {period}月",
            data={
                "period": period,
                "salary_base_data": mock_salary_base,
                "total_salary": sum(r["final_salary"] for r in mock_salary_base),
                "total_employees": len(mock_salary_base),
                "note": "工资表基础数据生成需要openpyxl支持，当前返回模拟数据"
            }
        )
