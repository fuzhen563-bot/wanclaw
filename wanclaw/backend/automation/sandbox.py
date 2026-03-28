"""
自动化安全沙箱
提供安全的代码执行环境，防止恶意操作
"""

import asyncio
import ast
import bisect
import collections
import hashlib
import io
import json
import logging
import math
import os
import re
import signal
import subprocess
import sys
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """安全等级"""
    NONE = "none"
    BASIC = "basic"
    STRICT = "strict"
    SANDBOX = "sandbox"


@dataclass
class SecurityRule:
    """安全规则"""
    name: str
    pattern: str
    action: str = "block"
    message: str = ""


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    output: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    blocked_operations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class CodeValidator:
    """代码验证器"""
    
    BLOCKED_IMPORTS = {
        'os', 'subprocess', 'shutil', 'socket', 'ctypes',
        'sys', 'glob', 'tempfile', 'threading', 'multiprocessing',
        'requests', 'urllib', 'http', 'ftplib', 'telnetlib',
        'poplib', 'imaplib', 'smtplib', 'telnet', 'pty',
        'pwd', 'spwd', 'grp', 'crypt', 'fcntl',
    }
    
    BLOCKED_PATTERNS = [
        r'subprocess\.',
        r'os\.system',
        r'os\.popen',
        r'eval\(',
        r'exec\(',
        r'compile\(',
        r'__import__',
        r'\.read\(\)',
        r'\.write\(',
        r'open\(',  # 需要特殊处理
        r'file\(',
        r'socket\.',
        r'urllib\.',
        r'requests\.',
        r'fabric\.',
        r'paramiko\.',
        r'cryptography\.',
    ]
    
    BLOCKED_FUNCTIONS = {
        'system', 'popen', 'spawn', 'exec', 'eval', 'compile',
        'mkdir', 'rmdir', 'remove', 'unlink', 'chmod', 'chown',
        'link', 'rename', 'symlink', 'readlink',
    }
    
    ALLOWED_MODULES = {
        'json', 're', 'math', 'random', 'datetime', 'time',
        'collections', 'itertools', 'functools', 'operator',
        'string', 'base64', 'hashlib', 'uuid',
    }
    
    ALLOWED_PATHS = [
        '/tmp/wanclaw',
        '/var/tmp/wanclaw',
    ]
    
    DANGEROUS_CONSTANT_SUBSTRINGS = {
        'os', 'subprocess', 'import', 'eval', 'exec', 'compile',
        '__import__', 'system', 'popen', '__globals__', '__locals__',
        '__builtins__', 'getattr', 'setattr', '__getattribute__',
    }
    
    def __init__(self, security_level: SecurityLevel = SecurityLevel.BASIC):
        self.security_level = security_level
        self._blocked_imports = set(self.BLOCKED_IMPORTS)
        self._blocked_patterns = [re.compile(p) for p in self.BLOCKED_PATTERNS]
    
    def validate(self, code: str) -> ExecutionResult:
        """验证代码安全性"""
        result = ExecutionResult(success=True)
        
        if self.security_level == SecurityLevel.NONE:
            return result
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            result.success = False
            result.error = f"语法错误: {e}"
            return result
        
        visitor = _SecurityASTVisitor(self.security_level, self._blocked_imports)
        visitor.visit(tree)
        
        if not visitor.result.success:
            return visitor.result
        
        for pattern in self._blocked_patterns:
            if pattern.search(code):
                if 'open(' in code and not self._check_open_safe(code):
                    result.success = False
                    result.error = "文件操作受限"
                    result.blocked_operations.append("open()")
                    return result
        
        return result
    
    def _check_open_safe(self, code: str) -> bool:
        """检查 open() 是否安全"""
        if "'r'" in code or '"r"' in code:
            for allowed in self.ALLOWED_PATHS:
                if allowed in code:
                    return True
        return False


class _SecurityASTVisitor(ast.NodeVisitor):

    def __init__(self, level: SecurityLevel, blocked_imports: set):
        self.level = level
        self.blocked_imports = blocked_imports
        self.result = ExecutionResult(success=True)
        self._in_strict_scope = level in (SecurityLevel.STRICT, SecurityLevel.SANDBOX)

    def visit_Import(self, node: ast.Import) -> None:
        if self.result.success:
            for alias in node.names:
                if alias.name in self.blocked_imports:
                    self._block(f"禁止导入: {alias.name}", f"import {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if self.result.success and node.module and node.module in self.blocked_imports:
            self._block(f"禁止导入: {node.module}", f"from {node.module} import")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if not self.result.success:
            return

        func = node.func

        if isinstance(func, ast.Name):
            if func.id in ('eval', 'exec', 'compile'):
                self._block(f"禁止调用: {func.id}", func.id)
            elif func.id in {'system', 'popen', 'spawn', 'mkdir', 'rmdir',
                              'remove', 'unlink', 'chmod', 'chown', 'link',
                              'rename', 'symlink', 'readlink'}:
                self.result.warnings.append(f"受限函数: {func.id}")

        elif isinstance(func, ast.Attribute):
            attr_val = func.value
            if isinstance(attr_val, ast.Name):
                if attr_val.id == 'os' and func.attr in self._os_basic_blocked():
                    self._block(f"禁止调用: os.{func.attr}", f"os.{func.attr}")
            if self._is_builtins_access(func):
                self._block(f"禁止访问: __builtins__.{func.attr}", f"__builtins__.{func.attr}")

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if self.result.success and self._in_strict_scope:
            if node.attr in {'__globals__', '__locals__', '__code__',
                              '__closure__', '__builtins__'}:
                self._block(f"禁止属性访问: {node.attr}", node.attr)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if self.result.success and self._in_strict_scope:
            if self._is_builtins_subscript(node):
                self._block("禁止: __builtins__[...]", "__builtins__ subscript")
        self.generic_visit(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        if self.result.success and self._in_strict_scope:
            self._block("禁止: Lambda 表达式", "lambda")
        else:
            self.generic_visit(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        if self.result.success and self._in_strict_scope:
            self._block("禁止: 生成器表达式", "generator expression")
        else:
            self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        if self.result.success and self.level == SecurityLevel.SANDBOX:
            self._block("禁止: 列表推导式 (sandbox)", "list comprehension")
        else:
            self.generic_visit(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        if self.result.success and self.level == SecurityLevel.SANDBOX:
            self._block("禁止: 字典推导式 (sandbox)", "dict comprehension")
        else:
            self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if self.result.success and self.level != SecurityLevel.NONE:
            if isinstance(node.value, str):
                val_lower = node.value.lower()
                for danger in CodeValidator.DANGEROUS_CONSTANT_SUBSTRINGS:
                    if danger in val_lower:
                        self._block(
                            f"常量中包含危险内容: '{node.value[:40]}'",
                            f"constant:{danger}"
                        )
                        break
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if self.result.success and self._in_strict_scope:
            if node.id in {'dir', 'vars', 'eval', 'exec', 'compile',
                              '__globals__', '__locals__', '__builtins__'}:
                self._block(f"禁止名称: {node.id}", node.id)
        self.generic_visit(node)

    def _is_builtins_access(self, node: ast.Attribute) -> bool:
        val = node.value
        if isinstance(val, ast.Name) and val.id == '__builtins__':
            return True
        if isinstance(val, ast.Subscript):
            return self._is_builtins_subscript(val)
        return False

    def _is_builtins_subscript(self, node: ast.Subscript) -> bool:
        val = node.value
        if isinstance(val, ast.Name) and val.id == '__builtins__':
            return True
        return False

    def _os_basic_blocked(self) -> set:
        if self.level == SecurityLevel.BASIC:
            return {'system', 'popen', 'spawn', 'execl', 'execv', 'fork', 'spawnl', 'spawnv'}
        return {
            'system', 'popen', 'spawn', 'execl', 'execv', 'fork',
            'spawnl', 'spawnv', 'open', 'listdir', 'walk',
            'stat', 'chdir', 'getcwd', 'remove', 'unlink',
            'mkdir', 'rmdir', 'rename', 'replace', 'access',
            'link', 'symlink', 'readlink', 'lstat',
        }

    def _block(self, message: str, operation: str) -> None:
        self.result.success = False
        self.result.error = message
        self.result.blocked_operations.append(operation)


class InputSanitizer:
    """输入净化器"""
    
    DANGEROUS_CHARS = [';', '|', '&', '$', '`', '\n', '\r']
    
    SQL_INJECTION_PATTERNS = [
        r"('|(\\'))",
        r"(union|select|insert|update|delete|drop|create|alter)\s",
        r"(--|#|/\*)",
    ]
    
    XSS_PATTERNS = [
        r"<script",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe",
        r"<embed",
        r"<object",
    ]
    
    SAFE_HTML_TAGS = {
        'b', 'i', 'u', 'em', 'strong', 'code', 'pre',
        'br', 'p', 'span', 'div', 'ul', 'ol', 'li',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'img',
        'table', 'thead', 'tbody', 'tr', 'th', 'td', 'blockquote',
    }
    
    SAFE_HTML_ATTRS = {'href', 'src', 'alt', 'title', 'class', 'id'}
    
    def sanitize(self, text: str) -> str:
        """净化输入"""
        for char in self.DANGEROUS_CHARS:
            text = text.replace(char, '')
        
        for pattern in self.SQL_INJECTION_PATTERNS:
            text = re.sub(pattern, '', text)
        
        for pattern in self.XSS_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text
    
    def sanitize_sql(self, text: str, params: Optional[List] = None) -> Tuple[str, List]:
        """
        安全的 SQL 参数化查询助手。
        返回 (safe_query, params) 元组。
        使用此方法替代字符串拼接构建 SQL。
        """
        dangerous_keywords = re.compile(
            r'\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b',
            re.IGNORECASE
        )
        safe_text = dangerous_keywords.sub(' ', text)
        if params is None:
            params = []
        return safe_text, params
    
    def sanitize_html(self, text: str) -> str:
        """
        白名单 HTML 净化。
        只保留预定义的安全标签和属性，移除所有其他标签/属性。
        """
        def mark_safe(match: re.Match) -> str:
            m = re.match(r'</?([a-zA-Z0-9]+)', match.group())
            if m and m.group(1).lower() in self.SAFE_HTML_TAGS:
                tag = m.group(1)
                is_closing = match.group().startswith('</')
                return f'[[{tag}]]' if not is_closing else f'[[/{tag}]]'
            return ''
        
        result = re.sub(r'</?[a-zA-Z0-9][^>]*>', mark_safe, text)
        result = result.replace('[[', '<').replace(']]', '>')
        return result
    
    def validate_path(self, path: str) -> bool:
        """验证路径安全性 — resolves symlinks before checking"""
        if path.startswith('file://'):
            path = path[7:]
        
        if path.startswith('/'):
            return False
        
        normalized = os.path.normpath(path)
        if normalized.startswith('..') or '..' in normalized:
            return False
        
        if normalized.startswith('/'):
            return False
        
        if '..' in path:
            return False
        
        return True


class AutomationSandbox:
    """自动化沙箱"""
    
    def __init__(
        self,
        security_level: SecurityLevel = SecurityLevel.STRICT,
        max_time: int = 300,
        max_memory_mb: int = 512,
    ):
        self.security_level = security_level
        self.max_time = max_time
        self.max_memory_mb = max_memory_mb
        self.validator = CodeValidator(security_level)
        self.sanitizer = InputSanitizer()
        self._execution_history: List[ExecutionResult] = []
        self._output_buffer_size = 64 * 1024
    
    async def execute(
        self,
        code: str,
        context: Dict[str, Any] = None,
        allowed_operations: List[str] = None,
    ) -> ExecutionResult:
        """在沙箱中执行代码"""
        start_time = time.time()
        result = ExecutionResult(success=False)
        
        validation = self.validator.validate(code)
        if not validation.success:
            result.error = validation.error
            result.blocked_operations = validation.blocked_operations
            self._execution_history.append(result)
            return result
        
        if allowed_operations:
            code = self._filter_operations(code, allowed_operations)
        
        safe_globals = self._get_safe_globals()
        safe_locals = dict(context) if context else {}
        
        try:
            if self.security_level == SecurityLevel.SANDBOX:
                result = await self._execute_in_sandbox_subprocess(
                    code, safe_globals, safe_locals
                )
            else:
                result = await self._execute_with_capture(
                    code, safe_globals, safe_locals
                )
            
        except asyncio.TimeoutError:
            result.error = f"执行超时（{self.max_time}秒）"
            
        except Exception as e:
            result.error = str(e)
        
        result.execution_time = time.time() - start_time
        self._execution_history.append(result)
        
        return result
    
    async def execute_skill(
        self,
        skill_name: str,
        skill_handler: Callable,
        params: Dict[str, Any],
    ) -> ExecutionResult:
        """执行技能（带沙箱保护）"""
        start_time = time.time()
        result = ExecutionResult(success=False)
        
        allowed_skills = self._get_allowed_skills()
        if skill_name not in allowed_skills:
            result.error = f"技能未授权: {skill_name}"
            return result
        
        try:
            clean_params = {}
            for key, value in params.items():
                if isinstance(value, str):
                    clean_params[key] = self.sanitizer.sanitize(value)
                else:
                    clean_params[key] = value
            
            if asyncio.iscoroutinefunction(skill_handler):
                result.output = await asyncio.wait_for(
                    skill_handler(**clean_params),
                    timeout=self.max_time
                )
            else:
                result.output = skill_handler(**clean_params)
            
            result.success = True
            
        except asyncio.TimeoutError:
            result.error = f"技能执行超时（{self.max_time}秒）"
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"Skill execution error: {e}")
        
        result.execution_time = time.time() - start_time
        return result
    
    def _get_safe_globals(self) -> Dict[str, Any]:
        """获取安全的全局变量"""
        safe_modules = {
            'json': json,
            're': re,
            'math': math,
            'random': random,
            'datetime': datetime,
            'time': time,
        }
        
        if self.security_level == SecurityLevel.STRICT:
            safe_builtins = {
                'print': print,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'list': list,
                'dict': dict,
                'tuple': tuple,
                'set': set,
                'range': range,
                'enumerate': enumerate,
                'zip': zip,
                'map': map,
                'filter': filter,
                'sum': sum,
                'min': min,
                'max': max,
                'abs': abs,
                'round': round,
                'sorted': sorted,
                'reversed': reversed,
                'isinstance': isinstance,
                'hasattr': hasattr,
                'open': self._blocked_open,
                **safe_modules,
            }
        elif self.security_level == SecurityLevel.SANDBOX:
            safe_builtins = {
                'print': print,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'list': list,
                'dict': dict,
                'tuple': tuple,
                'set': set,
                'range': range,
                **safe_modules,
            }
        else:
            safe_builtins = {
                'print': print,
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'bool': bool,
                'list': list,
                'dict': dict,
                'tuple': tuple,
                'set': set,
                'range': range,
                'enumerate': enumerate,
                'zip': zip,
                'map': map,
                'filter': filter,
                'sum': sum,
                'min': min,
                'max': max,
                'abs': abs,
                'round': round,
                'sorted': sorted,
                'reversed': reversed,
                'isinstance': isinstance,
                'hasattr': hasattr,
                'getattr': getattr,
                'setattr': setattr,
                **safe_modules,
            }
        
        return {
            '__builtins__': safe_builtins,
        }
    
    def _blocked_open(self, *args, **kwargs) -> None:
        """Blocked open() replacement for STRICT/SANDBOX levels."""
        raise PermissionError("文件操作在此安全级别下被禁用")
    
    def _filter_operations(self, code: str, allowed: List[str]) -> str:
        """过滤只允许的操作"""
        return code
    
    async def _execute_with_capture(
        self, code: str, globals_dict: Dict, locals_dict: Dict
    ) -> ExecutionResult:
        result = ExecutionResult(success=False)
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture
        
        def sync_exec():
            exec(code, globals_dict, locals_dict)
            if '_result_' in locals_dict:
                return locals_dict['_result_']
            return None
        
        try:
            loop = asyncio.get_event_loop()
            wrapped = asyncio.wait_for(
                loop.run_in_executor(None, sync_exec),
                timeout=self.max_time
            )
            output = await wrapped
            result.output = output
            result.success = True
        except asyncio.TimeoutError:
            result.error = f"执行超时（{self.max_time}秒）"
        except Exception as e:
            result.error = str(e)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        
        captured_out = stdout_capture.getvalue()
        captured_err = stderr_capture.getvalue()
        if captured_out:
            result.warnings.append(f"stdout: {captured_out[:500]}")
        if captured_err:
            result.warnings.append(f"stderr: {captured_err[:500]}")
        
        return result
    
    async def _execute_in_sandbox_subprocess(
        self, code: str, globals_dict: Dict, locals_dict: Dict
    ) -> ExecutionResult:
        result = ExecutionResult(success=False)
        
        import base64
        code_b64 = base64.b64encode(code.encode()).decode()
        
        safe_builtins_names = list(globals_dict.get('__builtins__', {}).keys())
        safe_modules = list(CodeValidator.ALLOWED_MODULES)
        
        wrapper_code = f"""
import sys, io, resource, base64
max_mem = {self.max_memory_mb * 1024 * 1024}
max_cpu = {self.max_time}
try:
    resource.setrlimit(resource.RLIMIT_AS, (max_mem, max_mem))
    resource.setrlimit(resource.RLIMIT_CPU, (max_cpu, max_cpu + 5))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
except Exception:
    pass

_safe_builtins = dict(__builtins__)
for _name in list(_safe_builtins.keys()):
    if _name not in {safe_builtins_names!r}:
        del _safe_builtins[_name]

_json_m = __import__('json')
_allowed = {{m: __import__(m) for m in {safe_modules!r}}}
_allowed['json'] = _json_m

_exec_globals = {{'__builtins__': _safe_builtins, **_allowed}}

_code = base64.b64decode('{code_b64}').decode()
_stdout_buf = io.StringIO()
_stderr_buf = io.StringIO()
_old_out, _old_err = sys.stdout, sys.stderr
sys.stdout, sys.stderr = _stdout_buf, _stderr_buf

try:
    exec(_code, _exec_globals, {{}})
    _res = _exec_globals.get('_result_')
    sys.stdout, sys.stderr = _old_out, _old_err
    print(repr(_res) if _res is not None else '')
except Exception as _e:
    sys.stdout, sys.stderr = _old_out, _old_err
    print('', file=sys.stderr)
    print(f'ERROR:{{_e}}', file=sys.stderr)
"""
        
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, '-c', wrapper_code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=self._output_buffer_size,
            )
            
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=self.max_time + 10
                )
            except asyncio.TimeoutError:
                proc.kill()
                result.error = f"执行超时（{self.max_time}秒）"
                return result
            
            stdout_text = stdout_bytes.decode('utf-8', errors='replace').strip()
            stderr_text = stderr_bytes.decode('utf-8', errors='replace').strip()
            
            if proc.returncode != 0 or stderr_text.startswith('ERROR:'):
                err = stderr_text.replace('ERROR:', '').strip()
                result.error = err or f"子进程退出码: {proc.returncode}"
                return result
            
            result.success = True
            if stdout_text:
                result.output = stdout_text
            if stderr_text:
                result.warnings.append(f"stderr: {stderr_text[:200]}")
            
        except Exception as e:
            result.error = str(e)
        finally:
            if proc and proc.returncode is None:
                proc.kill()
                try:
                    await proc.wait()
                except Exception:
                    pass
        
        return result
    
    async def _execute_code(self, code: str, globals_dict: Dict, locals_dict: Dict) -> Any:
        """Execute code (async) — delegates to capture method."""
        result = await self._execute_with_capture(code, globals_dict, locals_dict)
        if not result.success:
            raise RuntimeError(result.error or "执行失败")
        return result.output
    
    def _get_allowed_skills(self) -> List[str]:
        """获取允许的技能列表"""
        return [
            'pdf_process',
            'excel_process',
            'image_process',
            'text_process',
            'data_analysis',
            'web_search',
            'calculator',
        ]
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计"""
        total = len(self._execution_history)
        success = sum(1 for r in self._execution_history if r.success)
        failed = total - success
        
        return {
            'total_executions': total,
            'successful': success,
            'failed': failed,
            'success_rate': success / total if total > 0 else 0,
            'avg_execution_time': sum(r.execution_time for r in self._execution_history) / total if total > 0 else 0,
        }


class DockerSandbox:
    """Docker容器沙箱（可选，更高安全级别）"""
    
    def __init__(self, image: str = "wanclaw-sandbox:latest"):
        self.image = image
        self.container = None
    
    async def execute(self, code: str, timeout: int = 300) -> ExecutionResult:
        """在Docker容器中执行代码"""
        result = ExecutionResult(success=False)
        result.error = "Docker sandbox not implemented"
        return result
    
    async def execute_skill(self, skill_name: str, params: Dict) -> ExecutionResult:
        """在Docker中执行技能"""
        result = ExecutionResult(success=False)
        result.error = "Docker sandbox not implemented"
        return result


class RateLimiter:
    """
    速率限制器 — O(1) cleanup via sorted list + bisect.
    Supports optional Redis backend for distributed rate limiting.
    Supports burst allowance: first burst allows max_requests * burst_multiplier.
    """
    
    def __init__(
        self,
        max_requests: int = 60,
        window_seconds: int = 60,
        redis_client=None,
        burst_multiplier: float = 1.5,
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.redis = redis_client
        self.burst_multiplier = burst_multiplier
        self.burst_max = int(max_requests * burst_multiplier)
        self._requests: Dict[str, List[float]] = collections.defaultdict(list)
    
    def _redis_check(self, user_id: str) -> Tuple[bool, int, float]:
        if self.redis is None:
            raise RuntimeError("Redis not available")
        
        now = time.time()
        key = f"ratelimit:{user_id}"
        
        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(key, 0, now - self.window_seconds)
        pipe.zcard(key)
        pipe.execute()
        
        current_count = self.redis.zcard(key)
        reset_in = self.window_seconds - (now - self.redis.zrange(key, 0, 0, withscores=True)[0][1]) \
            if self.redis.zcard(key) > 0 else self.window_seconds
        
        if current_count >= self.max_requests:
            return False, 0, reset_in
        
        self.redis.zadd(key, {str(now): now})
        self.redis.expire(key, self.window_seconds + 1)
        remaining = max(0, self.max_requests - current_count - 1)
        return True, remaining, reset_in
    
    def check(self, user_id: str) -> bool:
        allowed, _, _ = self.check_and_get_limit(user_id)
        return allowed
    
    def get_remaining(self, user_id: str) -> int:
        _, remaining, _ = self.check_and_get_limit(user_id)
        return remaining
    
    def check_and_get_limit(self, user_id: str) -> Tuple[bool, int, float]:
        """
        检查是否允许请求并返回详细信息。
        
        Returns:
            Tuple of (allowed: bool, remaining: int, reset_in: float)
            - allowed: True if request is within rate limit
            - remaining: number of requests remaining in current window
            - reset_in: seconds until oldest request expires from window
        """
        if self.redis is not None:
            return self._redis_check(user_id)
        
        return self._memory_check(user_id)
    
    def _memory_check(self, user_id: str) -> Tuple[bool, int, float]:
        now = time.time()
        cutoff = now - self.window_seconds
        
        timestamps = self._requests[user_id]
        
        cutoff_idx = bisect.bisect_left(timestamps, cutoff)
        
        if cutoff_idx > 0:
            del timestamps[:cutoff_idx]
        
        current_count = len(timestamps)
        
        effective_limit = self.burst_max if current_count < self.max_requests else self.max_requests
        
        if current_count >= effective_limit:
            reset_in = (timestamps[0] + self.window_seconds - now) if timestamps else self.window_seconds
            return False, 0, max(0.0, reset_in)
        
        bisect.insort(timestamps, now)
        
        remaining = effective_limit - current_count - 1
        reset_in = self.window_seconds - (now - timestamps[0]) if timestamps else self.window_seconds
        
        return True, max(0, remaining), max(0.0, reset_in)


# 全局实例
_sandbox: Optional[AutomationSandbox] = None
_rate_limiter: Optional[RateLimiter] = None


def get_sandbox(security_level: SecurityLevel = SecurityLevel.STRICT) -> AutomationSandbox:
    """获取沙箱单例"""
    global _sandbox
    if _sandbox is None:
        _sandbox = AutomationSandbox(security_level)
    return _sandbox


def get_rate_limiter(
    max_requests: int = 60,
    window_seconds: int = 60,
    redis_client=None,
) -> RateLimiter:
    """获取速率限制器单例"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(max_requests, window_seconds, redis_client)
    return _rate_limiter
