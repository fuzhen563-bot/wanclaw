"""
WanClaw 插件安全模块
负责插件安全校验、版本兼容性检查、权限验证、AST代码分析
"""

import os
import re
import ast
import json
import hashlib
import zipfile
import logging
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

WANCLAW_VERSION = "2.0.0"  # 当前WanClaw版本


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityReport:
    """安全扫描报告"""
    safe: bool
    risk_level: RiskLevel
    warnings: List[str]
    errors: List[str]
    permissions_allowed: List[str]
    permissions_denied: List[str]
    scan_time: str = ""
    ast_findings: List[str] = field(default_factory=list)
    network_urls: List[str] = field(default_factory=list)
    suspicious_imports: List[str] = field(default_factory=list)
    audit_log: List[Dict] = field(default_factory=list)


class PluginSecurity:
    """插件安全校验器"""

    # 高危代码模式（regex）
    DANGEROUS_PATTERNS = [
        (r'os\.system\s*\(', '执行系统命令'),
        (r'subprocess\.(call|run|Popen)\s*\(', '创建子进程'),
        (r'eval\s*\(', '动态执行代码'),
        (r'exec\s*\(', '执行动态代码'),
        (r'__import__\s*\(', '动态导入'),
        (r'compile\s*\(', '编译代码'),
        (r'globals\s*\(\)', '访问全局变量'),
        (r'locals\s*\(\)', '访问局部变量'),
        (r'getattr\s*\(\s*\w+\s*,', '动态获取属性'),
        (r'setattr\s*\(\s*\w+\s*,', '动态设置属性'),
        (r'delattr\s*\(\s*\w+\s*,', '动态删除属性'),
        (r'open\s*\(\s*.*,\s*[\'"]w', '写文件'),
        (r'os\.remove\s*\(', '删除文件'),
        (r'os\.unlink\s*\(', '删除文件'),
        (r'shutil\.rmtree\s*\(', '删除目录'),
        (r'os\.makedirs\s*\(', '创建目录'),
        (r'os\.rename\s*\(', '重命名文件'),
        (r'chmod\s+', '修改权限'),
        (r'chown\s+', '修改所有者'),
    ]

    # 允许的权限
    ALLOWED_PERMISSIONS = [
        'network',           # 网络请求
        'filesystem:read',   # 只读文件系统
        'filesystem:write',  # 写文件系统（受限目录）
        'email',             # 发送邮件
        'database',          # 数据库访问
        'logging',           # 日志记录
        'config',            # 读取配置
    ]

    # 受限目录（插件可写）
    RESTRICTED_WRITE_DIRS = [
        './data/plugins/',
        './data/temp/',
        './plugins/*/data/',
    ]

    # 可疑的网络URL模式
    SUSPICIOUS_URL_PATTERNS = [
        r'https?://[^\s]*\.onion[^\s]*',  # Tor隐藏服务
        r'https?://[^\s]*\.i2p[^\s]*',    # I2P
        r'file://',                        # 本地文件协议
        r'ftp://',                         # FTP协议
    ]

    # 危险导入模块
    DANGEROUS_IMPORTS = {
        'ctypes', 'cffi', 'winreg', 'msilib',
        'socket', 'ssl', 'cryptography', 'paramiko',
        'requests', 'urllib3', 'httpx',  # 网络（需network权限）
    }

    def __init__(self, wanclaw_version: str = WANCLAW_VERSION):
        self.wanclaw_version = wanclaw_version

    def _audit_log(self, report: SecurityReport, action: str, detail: str, level: str = "info"):
        """记录审计日志"""
        entry = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "action": action,
            "detail": detail,
            "level": level,
        }
        report.audit_log.append(entry)
        getattr(logger, level)(f"[SECURITY_AUDIT] {action}: {detail}")

    def check_version_compatibility(self, required_version: str) -> Tuple[bool, str]:
        """检查版本兼容性
        
        支持格式:
        - ">=1.0.0" 大于等于
        - ">1.0.0" 大于
        - "<=1.0.0" 小于等于
        - "<1.0.0" 小于
        - "==1.0.0" 等于
        - "1.0.0" 等于
        - "*" 任意版本
        """
        if required_version == '*' or not required_version:
            return True, "兼容所有版本"
        
        def parse_version(v):
            parts = re.findall(r'\d+', v)
            return tuple(int(p) for p in parts[:3]) if parts else (0, 0, 0)
        
        current = parse_version(self.wanclaw_version)
        
        match = re.match(r'^(>=|<=|>|<|==)?\s*(.+)$', required_version)
        if not match:
            return False, f"无效的版本格式: {required_version}"
        
        op = match.group(1) or '=='
        required = parse_version(match.group(2))
        
        result = False
        if op == '>=':
            result = current >= required
        elif op == '>':
            result = current > required
        elif op == '<=':
            result = current <= required
        elif op == '<':
            result = current < required
        elif op == '==':
            result = current == required
        
        msg = f"WanClaw {self.wanclaw_version} {'兼容' if result else '不兼容'} 要求 {required_version}"
        return result, msg

    def scan_code(self, code: str, filename: str = "") -> List[Tuple[str, str]]:
        """扫描代码安全（regex方式）"""
        findings = []
        for pattern, desc in self.DANGEROUS_PATTERNS:
            if re.search(pattern, code):
                findings.append((filename, desc))
        return findings

    def scan_code_ast(self, code: str, filename: str = "") -> List[str]:
        """使用AST深度分析代码安全"""
        findings = []
        try:
            tree = ast.parse(code)
            finder = _DangerousCodeFinder(filename)
            finder.visit(tree)
            findings = finder.findings
        except SyntaxError as e:
            findings.append(f"{filename}: AST解析错误 - {e}")
        except Exception as e:
            findings.append(f"{filename}: AST扫描异常 - {e}")
        return findings

    def analyze_imports(self, code: str, filename: str = "") -> Tuple[List[str], List[str]]:
        """分析导入的模块，区分安全和不安全的"""
        safe_imports = []
        dangerous_imports = []

        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.name.split('.')[0]
                        if name in self.DANGEROUS_IMPORTS:
                            dangerous_imports.append(f"{filename}: {name}")
                        else:
                            safe_imports.append(name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        name = node.module.split('.')[0]
                        if name in self.DANGEROUS_IMPORTS:
                            dangerous_imports.append(f"{filename}: {node.module}")
                        else:
                            safe_imports.append(node.module)
        except Exception:
            pass

        return safe_imports, dangerous_imports

    def analyze_network_urls(self, code: str, filename: str = "") -> List[str]:
        """分析代码中的网络URL请求"""
        urls = []
        for pattern in self.SUSPICIOUS_URL_PATTERNS:
            for match in re.finditer(pattern, code, re.IGNORECASE):
                urls.append(f"{filename}: {match.group()}")
        
        # 也检查httpx/requests调用中的URL参数
        url_patterns = [
            r'(?:httpx|requests|urllib)\.(?:get|post|put|delete|request)\s*\(\s*["\']([^"\']+)["\']',
            r'["\'](https?://[^"\']+)["\']',
        ]
        for pattern in url_patterns:
            for match in re.finditer(pattern, code, re.IGNORECASE):
                url = match.group(1)
                if any(s in url for s in ['onion', 'i2p', 'file://', 'ftp://']):
                    urls.append(f"{filename}: {url}")
        
        return urls

    def validate_permissions(self, declared_permissions: List[str], report: SecurityReport = None) -> Tuple[List[str], List[str]]:
        """验证权限声明"""
        allowed = []
        denied = []

        for perm in declared_permissions:
            perm_lower = perm.lower().strip()

            if any(perm_lower.startswith(ap.lower()) for ap in self.ALLOWED_PERMISSIONS):
                allowed.append(perm)
            elif any(hr in perm_lower for hr in ['exec', 'shell', 'system', 'admin', 'root']):
                denied.append(perm)
                logger.warning(f"High-risk permission denied: {perm}")
                if report:
                    self._audit_log(report, "PERMISSION_DENIED", f"高危权限被拒绝: {perm}", "warning")
            else:
                allowed.append(perm)
                logger.info(f"Unknown permission allowed: {perm}")

        return allowed, denied

    def scan_plugin_zip(self, zip_path: str) -> SecurityReport:
        """扫描插件ZIP包（综合安全扫描）"""
        warnings = []
        errors = []
        risk_level = RiskLevel.LOW
        ast_findings: List[str] = []
        network_urls: List[str] = []
        suspicious_imports: List[str] = []
        audit_log: List[Dict] = []

        report = SecurityReport(
            safe=True,
            risk_level=RiskLevel.LOW,
            warnings=warnings,
            errors=errors,
            permissions_allowed=[],
            permissions_denied=[],
        )

        self._audit_log(report, "SCAN_START", f"开始扫描插件: {zip_path}")

        try:
            if not zipfile.is_zipfile(zip_path):
                self._audit_log(report, "SCAN_FAIL", "无效的ZIP文件", "error")
                return SecurityReport(
                    safe=False,
                    risk_level=RiskLevel.CRITICAL,
                    warnings=[],
                    errors=["无效的ZIP文件"],
                    permissions_allowed=[],
                    permissions_denied=[]
                )

            with zipfile.ZipFile(zip_path, 'r') as zf:
                files = zf.namelist()

                # 检查必需文件
                required_files = ['plugin.json']
                for req in required_files:
                    if not any(req in f for f in files):
                        errors.append(f"缺少必需文件: {req}")
                        risk_level = RiskLevel.HIGH
                        self._audit_log(report, "MISSING_FILE", f"缺少必需文件: {req}", "error")

                # 读取插件清单
                manifest = None
                manifest_file = next((f for f in files if f.endswith('plugin.json')), None)
                if manifest_file:
                    try:
                        manifest = json.loads(zf.read(manifest_file).decode('utf-8'))
                        self._audit_log(report, "MANIFEST_LOADED", f"成功加载manifest: {manifest_file}")
                    except Exception as e:
                        errors.append(f"plugin.json 格式错误: {e}")
                        risk_level = RiskLevel.HIGH
                        self._audit_log(report, "MANIFEST_ERROR", str(e), "error")

                # 检查权限
                allowed_perms = []
                denied_perms = []
                if manifest:
                    permissions = manifest.get('permissions', [])
                    allowed_perms, denied_perms = self.validate_permissions(permissions, report)
                    if denied_perms:
                        warnings.append(f"高危权限被拒绝: {', '.join(denied_perms)}")
                        risk_level = max(risk_level, RiskLevel.MEDIUM)
                else:
                    allowed_perms = []
                    denied_perms = []

                # 扫描代码文件（regex + AST + imports + network）
                for file_name in files:
                    if file_name.endswith(('.py', '.pyw')):
                        try:
                            content = zf.read(file_name).decode('utf-8', errors='ignore')

                            # 1. Regex扫描
                            findings = self.scan_code(content, file_name)
                            for fname, desc in findings:
                                warnings.append(f"{fname}: {desc}")
                                risk_level = max(risk_level, RiskLevel.HIGH)
                                self._audit_log(report, "DANGEROUS_PATTERN", f"{fname}: {desc}", "warning")

                            # 2. AST深度扫描
                            ast_results = self.scan_code_ast(content, file_name)
                            for finding in ast_results:
                                ast_findings.append(finding)
                                warnings.append(finding)
                                risk_level = max(risk_level, RiskLevel.HIGH)
                                self._audit_log(report, "AST_FINDING", finding, "warning")

                            # 3. 导入分析
                            safe_imp, danger_imp = self.analyze_imports(content, file_name)
                            for imp in danger_imp:
                                suspicious_imports.append(imp)
                                warnings.append(f"危险导入: {imp}")
                                self._audit_log(report, "DANGEROUS_IMPORT", imp, "warning")

                            # 4. 网络URL分析
                            urls = self.analyze_network_urls(content, file_name)
                            for url in urls:
                                network_urls.append(url)
                                warnings.append(f"可疑网络地址: {url}")
                                risk_level = max(risk_level, RiskLevel.MEDIUM)
                                self._audit_log(report, "SUSPICIOUS_URL", url, "warning")

                        except Exception as e:
                            warnings.append(f"无法扫描 {file_name}: {e}")
                            self._audit_log(report, "SCAN_ERROR", f"无法扫描 {file_name}: {e}", "warning")

                # 检查文件大小
                total_size = sum(zf.getinfo(f).file_size for f in files)
                if total_size > 50 * 1024 * 1024:  # 50MB
                    warnings.append(f"插件大小超过50MB: {total_size / 1024 / 1024:.1f}MB")
                    risk_level = max(risk_level, RiskLevel.MEDIUM)
                    self._audit_log(report, "SIZE_WARNING", f"插件大小{total_size / 1024 / 1024:.1f}MB", "info")

                # 检查目录遍历
                for file_name in files:
                    if '..' in file_name or file_name.startswith('/'):
                        errors.append(f"危险的文件路径: {file_name}")
                        risk_level = RiskLevel.CRITICAL
                        self._audit_log(report, "PATH_TRAVERSAL", f"危险路径: {file_name}", "error")

                # 检查压缩包炸弹（高压缩率文件）
                for file_name in files:
                    info = zf.getinfo(file_name)
                    if info.file_size > 0 and info.compress_size / info.file_size < 0.01:
                        warnings.append(f"疑似压缩包炸弹: {file_name} (压缩率异常)")
                        risk_level = max(risk_level, RiskLevel.HIGH)
                        self._audit_log(report, "ZIPBOMB", f"疑似压缩包炸弹: {file_name}", "warning")

                is_safe = risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]
                self._audit_log(report, "SCAN_COMPLETE", f"扫描完成, safe={is_safe}, risk={risk_level.value}")

                return SecurityReport(
                    safe=is_safe,
                    risk_level=risk_level,
                    warnings=warnings,
                    errors=errors,
                    permissions_allowed=allowed_perms,
                    permissions_denied=denied_perms,
                    ast_findings=ast_findings,
                    network_urls=network_urls,
                    suspicious_imports=suspicious_imports,
                    audit_log=audit_log,
                )

        except Exception as e:
            self._audit_log(report, "SCAN_EXCEPTION", str(e), "error")
            return SecurityReport(
                safe=False,
                risk_level=RiskLevel.CRITICAL,
                warnings=[],
                errors=[f"扫描失败: {str(e)}"],
                permissions_allowed=[],
                permissions_denied=[],
                audit_log=audit_log,
            )

    def verify_signature(self, file_path: str, expected_signature: str) -> bool:
        """验证文件签名"""
        if not expected_signature:
            return True

        try:
            with open(file_path, 'rb') as f:
                actual_hash = hashlib.sha256(f.read()).hexdigest()
            return actual_hash == expected_signature
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False

    def calculate_signature(self, file_path: str) -> str:
        """计算文件签名"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return ""


class _DangerousCodeFinder(ast.NodeVisitor):
    """AST visitor for finding dangerous code patterns"""

    def __init__(self, filename: str = ""):
        self.filename = filename
        self.findings: List[str] = []

    def visit_Call(self, node: ast.Call):
        # 检查危险函数调用
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        dangerous_calls = {
            'system': 'os.system() - 执行系统命令',
            'popen': 'subprocess.Popen - 创建子进程',
            'call': 'subprocess.call - 创建子进程',
            'run': 'subprocess.run - 创建子进程',
            'eval': 'eval() - 动态执行代码',
            'exec': 'exec() - 执行动态代码',
            '__import__': '__import__() - 动态导入',
            'compile': 'compile() - 编译代码',
            'open': 'open() - 文件操作',
            'getattr': 'getattr() - 动态获取属性',
            'setattr': 'setattr() - 动态设置属性',
            'delattr': 'delattr() - 动态删除属性',
        }

        if func_name in dangerous_calls:
            self.findings.append(f"{self.filename}: {dangerous_calls[func_name]}")

        # 检查危险导入
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            if alias.name in {'ctypes', 'cffi', 'winreg', 'msilib'}:
                self.findings.append(f"{self.filename}: 危险模块导入 - {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module and node.module.split('.')[0] in {'ctypes', 'cffi', 'winreg', 'msilib'}:
            self.findings.append(f"{self.filename}: 危险模块导入 - {node.module}")
        self.generic_visit(node)


# 全局安全实例
_plugin_security: Optional[PluginSecurity] = None


def get_plugin_security(**kwargs) -> PluginSecurity:
    """获取全局安全实例"""
    global _plugin_security
    if _plugin_security is None:
        _plugin_security = PluginSecurity(**kwargs)
    return _plugin_security
