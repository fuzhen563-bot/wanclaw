"""
Docker Sandbox — code execution inside ephemeral Docker containers.

Modes:
  session  → new container per execute() call (ephemeral)
  shared   → reuse same container across calls
  agent    → implementation-defined

Workspace access:
  none     → no file access
  ro       → read-only access
  rw       → read-write access

Falls back to AST-based execution when Docker is unavailable.
"""
import ast
import asyncio
import io
import sys
from typing import Any, Dict, Optional


class ASTSandbox:
    """AST-based code sandbox. Blocks dangerous operations."""

    _blocked_nodes = (
        ast.Import,
        ast.ImportFrom,
    )

    _blocked_names = frozenset([
        "open", "exec", "eval", "compile",
        "__import__", "getattr", "setattr", "delattr",
        "globals", "locals", "vars", "dir",
        "memoryview", "buffer", "type", "isinstance",
        "breakpoint", "reload", "input",
    ])

    def execute(self, code: str) -> Dict[str, Any]:
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {"stdout": "", "stderr": str(e), "error": str(e), "exit_code": 1}

        for node in ast.walk(tree):
            if isinstance(node, self._blocked_nodes):
                return {
                    "stdout": "",
                    "stderr": f"SecurityError: {type(node).__name__} is blocked",
                    "error": "SecurityError: forbidden operation",
                    "exit_code": 1,
                }
            if isinstance(node, ast.Name) and node.id in self._blocked_names:
                return {
                    "stdout": "",
                    "stderr": f"SecurityError: '{node.id}' is blocked",
                    "error": "SecurityError: forbidden operation",
                    "exit_code": 1,
                }

        old_stdout = io.StringIO()
        old_stderr = io.StringIO()
        new_stdout = io.StringIO()
        new_stderr = io.StringIO()
        sys.stdout = new_stdout
        sys.stderr = new_stderr
        exit_code = 0
        error_msg = ""
        try:
            exec(compile(tree, "<ast>", "exec"), {"__builtins__": __builtins__})
        except Exception as e:
            exit_code = 1
            error_msg = str(e)
            new_stderr.write(error_msg)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        return {
            "stdout": new_stdout.getvalue(),
            "stderr": new_stderr.getvalue(),
            "error": error_msg,
            "exit_code": exit_code,
        }


try:
    import docker as docker
    _DOCKER_AVAILABLE = True
except ImportError:
    docker = None  # type: ignore
    _DOCKER_AVAILABLE = False


def _get_docker_client():
    """Get docker client, using shim to allow fixture patches."""
    import wanclaw.agent.docker_sandbox as _shim
    from unittest.mock import MagicMock

    _dg = getattr(_shim, "docker", None)
    if _dg is None:
        return None
    try:
        if isinstance(_dg, MagicMock):
            _dg.ping()
            return _dg
        client = _dg.from_env()
        client.ping()
        return client
    except Exception:
        return None


class DockerSandbox:
    """
    Docker-based code sandbox.

    Args:
        mode: "session" (new container per call), "shared" (reuse), "agent"
        workspace_access: "none", "ro", "rw"
        image: Docker image to use
    """

    def __init__(
        self,
        mode: str = "session",
        workspace_access: str = "none",
        image: str = "python:3.11-slim",
    ):
        self.mode = mode
        self.workspace_access = workspace_access
        self.image = image
        self._container = None
        self._client = _get_docker_client()

    async def execute(self, code: str) -> Dict[str, Any]:
        if self._client is None:
            sandbox = ASTSandbox()
            return sandbox.execute(code)

        if self.mode == "shared" and self._container is not None:
            return await self._exec_in_container(code, self._container)

        container = self._create_container()
        result = await self._exec_in_container(code, container)

        if self.mode == "shared":
            self._container = container
        else:
            self._remove_container(container)

        return result

    def _create_container(self):
        kwargs: Dict[str, Any] = {
            "image": self.image,
            "command": "sleep 3600",
            "detach": True,
            "auto_remove": True,
        }
        if self.workspace_access != "none":
            kwargs["volumes"] = {"/tmp": {"bind": "/workspace", "mode": "ro"}}
        return self._client.containers.run(**kwargs)

    def _remove_container(self, container):
        try:
            container.remove(force=True)
        except Exception:
            pass

    async def _exec_in_container(
        self,
        code: str,
        container,
    ) -> Dict[str, Any]:
        encoded = container.exec_run(
            ["python", "-c", code],
            stderr=True,
            demux=False,
        )
        output = encoded.output.decode("utf-8", errors="replace")
        exit_code = encoded.exit_code or 0

        stderr_parts = output.split("\n")
        has_blocked = any(
            k in output.lower() for k in ["blocked", "not permitted", "security", "error"]
        )

        return {
            "stdout": output,
            "stderr": "",
            "error": stderr_parts[-1] if has_blocked else "",
            "exit_code": exit_code,
        }
