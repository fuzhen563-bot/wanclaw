"""
安全扫描技能
扫描弱密码账号，防止误删系统文件
"""

import os
import pwd
import grp
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from wanclaw.backend.skills import BaseSkill, SkillResult, SkillCategory, SkillLevel


logger = logging.getLogger(__name__)


class SecurityScannerSkill(BaseSkill):
    """安全扫描技能"""
    
    def __init__(self):
        super().__init__()
        self.name = "SecurityScanner"
        self.description = "安全扫描：扫描弱密码账号，防止误删系统文件"
        self.category = SkillCategory.SECURITY
        self.level = SkillLevel.ADVANCED
        
        self.required_params = ["action"]
        
        self.optional_params = {
            "scan_type": str,
            "target_path": str,
            "check_weak_passwords": bool,
            "check_file_permissions": bool,
            "check_system_files": bool,
            "severity_threshold": str
        }
    
    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        action = params.get("action", "").lower()
        
        try:
            if action == "scan":
                return await self._security_scan(params)
            elif action == "weak_passwords":
                return await self._scan_weak_passwords(params)
            elif action == "file_permissions":
                return await self._scan_file_permissions(params)
            elif action == "system_files":
                return await self._check_system_files(params)
            elif action == "report":
                return await self._generate_report(params)
            else:
                return SkillResult(
                    success=False,
                    message=f"不支持的操作: {action}",
                    error=f"Unsupported action: {action}"
                )
        except Exception as e:
            logger.error(f"安全扫描失败: {action} - {e}")
            return SkillResult(
                success=False,
                message=f"安全扫描失败: {str(e)}",
                error=str(e)
            )
    
    async def _security_scan(self, params: Dict[str, Any]) -> SkillResult:
        scan_type = params.get("scan_type", "full")
        severity_threshold = params.get("severity_threshold", "medium")
        
        mock_findings = [
            {"type": "weak_password", "severity": "critical", "target": "root", "description": "root密码过于简单", "recommendation": "立即修改为强密码"},
            {"type": "weak_password", "severity": "high", "target": "admin", "description": "admin账户使用默认密码", "recommendation": "修改为非默认密码"},
            {"type": "file_permission", "severity": "high", "target": "/etc/shadow", "description": "shadow文件权限过宽", "recommendation": "限制为root-only访问"},
            {"type": "file_permission", "severity": "medium", "target": "/tmp", "description": "tmp目录可被所有用户写", "recommendation": "检查必要性"},
            {"type": "system_file", "severity": "low", "target": "/bin/ls", "description": "系统文件最近无修改", "recommendation": "正常"}
        ]
        
        severity_order = ["critical", "high", "medium", "low"]
        threshold_idx = severity_order.index(severity_threshold) if severity_threshold in severity_order else 3
        filtered_findings = [f for f in mock_findings if severity_order.index(f["severity"]) <= threshold_idx]
        
        return SkillResult(
            success=True,
            message=f"安全扫描完成，发现{len(filtered_findings)}个问题",
            data={
                "scan_type": scan_type,
                "severity_threshold": severity_threshold,
                "findings": filtered_findings,
                "total_findings": len(filtered_findings),
                "by_severity": {
                    "critical": len([f for f in filtered_findings if f["severity"] == "critical"]),
                    "high": len([f for f in filtered_findings if f["severity"] == "high"]),
                    "medium": len([f for f in filtered_findings if f["severity"] == "medium"]),
                    "low": len([f for f in filtered_findings if f["severity"] == "low"])
                },
                "scan_time": datetime.now().isoformat(),
                "note": "安全扫描，当前返回模拟数据"
            }
        )
    
    async def _scan_weak_passwords(self, params: Dict[str, Any]) -> SkillResult:
        check_weak_passwords = params.get("check_weak_passwords", True)
        
        if not check_weak_passwords:
            return SkillResult(
                success=True,
                message="弱密码扫描已跳过",
                data={"skipped": True}
            )
        
        mock_accounts = [
            {"username": "root", "uid": 0, "password_age_days": 365, "status": "weak", "issues": ["密码未更新超过1年", "密码包含用户名"]},
            {"username": "admin", "uid": 1000, "password_age_days": 180, "status": "weak", "issues": ["使用常见用户名", "密码过短"]},
            {"username": "test", "uid": 1001, "password_age_days": 90, "status": "medium", "issues": ["测试账户未清理"]},
            {"username": "deploy", "uid": 1002, "password_age_days": 30, "status": "strong", "issues": []}
        ]
        
        weak_accounts = [a for a in mock_accounts if a["status"] in ["weak", "medium"]]
        
        return SkillResult(
            success=True,
            message=f"弱密码扫描完成，{len(weak_accounts)}个账户存在风险",
            data={
                "accounts_scanned": len(mock_accounts),
                "weak_accounts": weak_accounts,
                "weak_count": len([a for a in weak_accounts if a["status"] == "weak"]),
                "medium_count": len([a for a in weak_accounts if a["status"] == "medium"]),
                "recommendations": [
                    "强制root账户使用强密码",
                    "禁用或删除test账户",
                    "定期轮换密码"
                ],
                "note": "弱密码扫描需要shadow文件读取权限，当前返回模拟数据"
            }
        )
    
    async def _scan_file_permissions(self, params: Dict[str, Any]) -> SkillResult:
        target_path = params.get("target_path", "/")
        
        mock_permissions = [
            {"path": "/etc/passwd", "mode": "644", "owner": "root", "group": "root", "status": "warning", "issue": "所有用户可读"},
            {"path": "/etc/shadow", "mode": "640", "owner": "root", "group": "root", "status": "ok", "issue": None},
            {"path": "/tmp", "mode": "1777", "owner": "root", "group": "root", "status": "info", "issue": "临时目录建议限制"},
            {"path": "/home", "mode": "755", "owner": "root", "group": "root", "status": "ok", "issue": None}
        ]
        
        issues = [p for p in mock_permissions if p["status"] != "ok"]
        
        return SkillResult(
            success=True,
            message=f"文件权限扫描完成，{len(issues)}个问题",
            data={
                "target_path": target_path,
                "files_scanned": len(mock_permissions),
                "issues": issues,
                "critical_issues": len([p for p in issues if p["status"] == "warning"]),
                "note": "文件权限扫描，当前返回模拟数据"
            }
        )
    
    async def _check_system_files(self, params: Dict[str, Any]) -> SkillResult:
        check_system_files = params.get("check_system_files", True)
        
        if not check_system_files:
            return SkillResult(
                success=True,
                message="系统文件检查已跳过",
                data={"skipped": True}
            )
        
        protected_paths = ["/bin", "/sbin", "/usr/bin", "/usr/sbin", "/etc"]
        
        mock_protected = [
            {"path": "/bin/ls", "status": "unchanged", "last_checked": datetime.now().isoformat()},
            {"path": "/bin/bash", "status": "unchanged", "last_checked": datetime.now().isoformat()},
            {"path": "/usr/bin/python3", "status": "unchanged", "last_checked": datetime.now().isoformat()}
        ]
        
        return SkillResult(
            success=True,
            message=f"系统文件检查完成，{len(mock_protected)}个受保护文件",
            data={
                "protected_paths": protected_paths,
                "files_checked": len(mock_protected),
                "protected_files": mock_protected,
                "changes_detected": 0,
                "protected": True,
                "note": "系统文件完整性检查，当前返回模拟数据"
            }
        )
    
    async def _generate_report(self, params: Dict[str, Any]) -> SkillResult:
        output_format = params.get("format", "json")
        
        mock_report = {
            "title": "安全扫描报告",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_issues": 5,
                "critical": 1,
                "high": 2,
                "medium": 1,
                "low": 1
            },
            "categories": {
                "weak_passwords": {"count": 2, "severity": "critical"},
                "file_permissions": {"count": 2, "severity": "high"},
                "system_files": {"count": 1, "severity": "low"}
            },
            "recommendations": [
                "立即修改root和admin账户密码",
                "限制/etc/shadow文件权限",
                "定期执行安全扫描"
            ]
        }
        
        return SkillResult(
            success=True,
            message="安全报告生成完成",
            data={
                "report": mock_report,
                "format": output_format,
                "note": "安全报告生成，当前返回模拟数据"
            }
        )
