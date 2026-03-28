"""
WanClaw Sandbox

Isolated execution environment for skills and tools.
Prevents untrusted code from accessing the host system.
"""

import os
import sys
import json
import logging
import subprocess
import tempfile
import time
import resource
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

BLOCKED_IMPORTS = ["os", "subprocess", "shutil", "socket", "ctypes", "sys"]
BLOCKED_FUNCTIONS = ["exec", "eval", "compile", "__import__", "open"]
ALLOWED_PATHS = ["/tmp", "/var/tmp"]


class SandboxViolation(Exception):
    pass


class Sandbox:
    def __init__(self, max_time: int = 30, max_memory_mb: int = 256, allowed_paths: list = None):
        self.max_time = max_time
        self.max_memory_mb = max_memory_mb
        self.allowed_paths = allowed_paths or ALLOWED_PATHS
        self._tmpdir = tempfile.mkdtemp(prefix="wanclaw_sandbox_")

    def _check_code_safety(self, code: str):
        for blocked in BLOCKED_IMPORTS:
            if f"import {blocked}" in code or f"from {blocked}" in code:
                raise SandboxViolation(f"Blocked import: {blocked}")
        for blocked in BLOCKED_FUNCTIONS:
            if f"{blocked}(" in code:
                raise SandboxViolation(f"Blocked function: {blocked}")

    def _check_path_safety(self, path: str):
        abs_path = os.path.abspath(path)
        if not any(abs_path.startswith(p) for p in self.allowed_paths):
            raise SandboxViolation(f"Path not allowed: {abs_path}")

    def execute_python(self, code: str, params: Dict = None) -> Dict:
        self._check_code_safety(code)
        wrapper = f"""
import json, sys, time
_params = {json.dumps(params or {})}
_start = time.time()
try:
{chr(10).join('    ' + line for line in code.split(chr(10)))}
    _result = run(_params) if 'run' in dir() else None
    print(json.dumps({{"success": True, "result": _result, "time": time.time() - _start}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e), "time": time.time() - _start}}))
"""
        script_path = os.path.join(self._tmpdir, f"script_{int(time.time())}.py")
        with open(script_path, "w") as f:
            f.write(wrapper)
        try:
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
                timeout=self.max_time,
                cwd=self._tmpdir,
            )
            try:
                return json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                return {"success": False, "error": result.stderr or "Unknown error"}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Execution timed out ({self.max_time}s)"}
        finally:
            try:
                os.unlink(script_path)
            except Exception:
                pass

    def execute_command(self, command: str, args: list = None) -> Dict:
        safe_commands = ["echo", "cat", "ls", "date", "whoami", "pwd", "wc"]
        cmd_name = command.split()[0] if command else ""
        if cmd_name not in safe_commands:
            raise SandboxViolation(f"Command not allowed: {cmd_name}")
        try:
            result = subprocess.run(
                [command] + (args or []),
                capture_output=True,
                text=True,
                timeout=self.max_time,
                cwd=self._tmpdir,
            )
            return {"success": result.returncode == 0, "stdout": result.stdout, "stderr": result.stderr}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Command timed out ({self.max_time}s)"}

    def cleanup(self):
        import shutil
        try:
            shutil.rmtree(self._tmpdir)
        except Exception:
            pass


_sandbox: Optional[Sandbox] = None


def get_sandbox(**kwargs) -> Sandbox:
    global _sandbox
    if _sandbox is None:
        _sandbox = Sandbox(**kwargs)
    return _sandbox
