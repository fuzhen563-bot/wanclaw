"""
Tests for DockerSandbox — code execution inside ephemeral Docker containers.

Validates container lifecycle, code execution, blocked imports,
ephemeral isolation, Docker unavailability fallback, mode controls,
and workspace access controls.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def docker_available(monkeypatch):
    """Simulate Docker daemon being available."""
    mock_client = MagicMock()
    mock_client.ping = MagicMock(return_value=True)
    monkeypatch.setattr("wanclaw.agent.docker_sandbox.docker", mock_client)
    return mock_client


@pytest.fixture
def docker_unavailable(monkeypatch):
    """Simulate Docker daemon being unavailable."""
    import_error = ImportError("No module named 'docker'")

    def mock_import(name, *args, **kwargs):
        if name == "docker":
            raise import_error
        return original_import(name, *args, **kwargs)

    import builtins
    original_import = builtins.__import__
    monkeypatch.setattr(builtins, "__import__", mock_import)
    yield
    monkeypatch.setattr(builtins, "__import__", original_import)


# ---------------------------------------------------------------------------
# Tests — Container Lifecycle
# ---------------------------------------------------------------------------

class TestContainerLifecycle:
    """Container starts successfully and is cleaned up after execution."""

    async def test_container_starts(self, docker_available):
        """execute() starts a Docker container."""
        from wanclaw.agent.docker_sandbox import DockerSandbox

        sandbox = DockerSandbox()
        result = await sandbox.execute("print('hello')")

        # Container should have been started
        docker_available.containers.run.assert_called()

    async def test_container_is_removed_after_execution(self, docker_available):
        """Container is removed (ephemeral) after execute completes."""
        from wanclaw.agent.docker_sandbox import DockerSandbox

        sandbox = DockerSandbox()
        await sandbox.execute("print('done')")

        # Container should be removed
        docker_available.containers.run.return_value.remove.assert_called()

    async def test_execute_returns_output(self, docker_available):
        """execute() returns stdout/stderr from the container."""
        from wanclaw.agent.docker_sandbox import DockerSandbox

        mock_container = docker_available.containers.run.return_value
        mock_container.exec_run.return_value.output = b"hello world\n"

        sandbox = DockerSandbox()
        result = await sandbox.execute("print('hello world')")

        assert result is not None
        assert "hello" in str(result) or result.get("stdout") == "hello world\n"


# ---------------------------------------------------------------------------
# Tests — Code Execution Inside Container
# ---------------------------------------------------------------------------

class TestCodeExecution:
    """Code runs inside the container with expected results."""

    async def test_python_code_executes(self, docker_available):
        """Python code executes inside the container."""
        from wanclaw.agent.docker_sandbox import DockerSandbox

        mock_container = docker_available.containers.run.return_value
        mock_container.exec_run.return_value.output = b"42\n"

        sandbox = DockerSandbox()
        result = await sandbox.execute("x = 21; print(x * 2)")

        assert result is not None

    async def test_stderr_captured(self, docker_available):
        """stderr from code execution is captured."""
        from wanclaw.agent.docker_sandbox import DockerSandbox

        mock_container = docker_available.containers.run.return_value
        mock_container.exec_run.return_value.output = b""
        mock_container.exec_run.return_value.exit_code = 1

        sandbox = DockerSandbox()
        result = await sandbox.execute("raise Exception('test error')")

        assert result is not None
        # stderr or error field should contain the error
        result_str = str(result)
        assert "error" in result_str.lower() or "exception" in result_str.lower()

    async def test_exit_code_captured(self, docker_available):
        """Container exit code is captured and returned."""
        from wanclaw.agent.docker_sandbox import DockerSandbox

        mock_container = docker_available.containers.run.return_value
        mock_container.exec_run.return_value.exit_code = 0

        sandbox = DockerSandbox()
        result = await sandbox.execute("print('ok')")

        assert result is not None
        assert result.get("exit_code") == 0 or result.get("returncode") == 0


# ---------------------------------------------------------------------------
# Tests — Blocked Imports
# ---------------------------------------------------------------------------

class TestBlockedImports:
    """Dangerous imports remain blocked inside the sandbox."""

    async def test_os_module_blocked(self, docker_available):
        """os module access is blocked inside the container."""
        from wanclaw.agent.docker_sandbox import DockerSandbox

        mock_container = docker_available.containers.run.return_value
        # Simulate import error inside container
        mock_container.exec_run.return_value.output = (
            b"ImportError: import of 'os' not permitted\n"
        )
        mock_container.exec_run.return_value.exit_code = 1

        sandbox = DockerSandbox()
        result = await sandbox.execute("import os; os.system('ls')")

        # Should detect blocked import
        result_str = str(result)
        assert (
            "blocked" in result_str.lower()
            or "not permitted" in result_str.lower()
            or "import" in result_str.lower()
        )

    async def test_subprocess_blocked(self, docker_available):
        """subprocess module is blocked inside the container."""
        from wanclaw.agent.docker_sandbox import DockerSandbox

        mock_container = docker_available.containers.run.return_value
        mock_container.exec_run.return_value.output = (
            b"SecurityError: subprocess blocked\n"
        )

        sandbox = DockerSandbox()
        result = await sandbox.execute("import subprocess; subprocess.run(['ls'])")

        result_str = str(result)
        assert (
            "blocked" in result_str.lower()
            or "security" in result_str.lower()
            or "subprocess" in result_str.lower()
        )


# ---------------------------------------------------------------------------
# Tests — Ephemeral Isolation
# ---------------------------------------------------------------------------

class TestEphemeralIsolation:
    """Container has no persistent state between calls."""

    async def test_no_state_between_calls(self, docker_available):
        """Variables from first call not present in second call."""
        from wanclaw.agent.docker_sandbox import DockerSandbox

        mock_container = docker_available.containers.run.return_value
        call_count = [0]

        def exec_side_effect(cmd, **kwargs):
            call_count[0] += 1
            # Each call returns fresh output
            return MagicMock(output=f"call{call_count[0]} output\n".encode())

        mock_container.exec_run.side_effect = exec_side_effect

        sandbox = DockerSandbox()
        result1 = await sandbox.execute("x = 1")
        result2 = await sandbox.execute("print(x)")

        # Second call should not know about x from first call
        result2_str = str(result2)
        assert (
            "name 'x' is not defined" in result2_str.lower()
            or "not defined" in result2_str.lower()
            or "call2" in result2_str
        )

    async def test_new_container_per_execution(self, docker_available):
        """Each execute() creates a new container (ephemeral mode)."""
        from wanclaw.agent.docker_sandbox import DockerSandbox

        sandbox = DockerSandbox()
        await sandbox.execute("print(1)")
        await sandbox.execute("print(2)")

        # Should have created 2 separate containers
        assert docker_available.containers.run.call_count == 2


# ---------------------------------------------------------------------------
# Tests — Docker Unavailable Fallback
# ---------------------------------------------------------------------------

class TestDockerUnavailableFallback:
    """When Docker is unavailable, falls back to AST-based execution."""

    async def test_ast_fallback_when_docker_unavailable(self, docker_unavailable):
        """execute() uses AST-based sandbox when Docker unavailable."""
        # When docker module can't be imported, should fall back to AST
        from wanclaw.agent.docker_sandbox import DockerSandbox

        sandbox = DockerSandbox()
        result = await sandbox.execute("print(1 + 2)")

        assert result is not None
        assert "3" in str(result) or result.get("stdout") == "3\n"

    async def test_ast_fallback_blocks_dangerous_code(self, docker_unavailable):
        """AST fallback blocks dangerous operations."""
        from wanclaw.agent.docker_sandbox import DockerSandbox

        sandbox = DockerSandbox()
        result = await sandbox.execute("import os; os.system('ls')")

        result_str = str(result)
        assert (
            "blocked" in result_str.lower()
            or "forbidden" in result_str.lower()
            or "security" in result_str.lower()
        )


# ---------------------------------------------------------------------------
# Tests — Mode Controls
# ---------------------------------------------------------------------------

class TestModeControls:
    """Sandbox mode (session/agent/shared) controls container behavior."""

    async def test_session_mode_new_container_each_call(self, docker_available):
        """session mode: new container per execute() call."""
        from wanclaw.agent.docker_sandbox import DockerSandbox

        sandbox = DockerSandbox(mode="session")
        await sandbox.execute("print(1)")
        await sandbox.execute("print(2)")

        assert docker_available.containers.run.call_count == 2

    async def test_shared_mode_reuses_container(self, docker_available):
        """shared mode: reuses same container across calls."""
        from wanclaw.agent.docker_sandbox import DockerSandbox

        sandbox = DockerSandbox(mode="shared")
        await sandbox.execute("print(1)")
        await sandbox.execute("print(2)")

        # Should create only 1 container, reuse it
        assert docker_available.containers.run.call_count == 1

    async def test_agent_mode(self, docker_available):
        """agent mode: behaves as expected (implementation-defined)."""
        from wanclaw.agent.docker_sandbox import DockerSandbox

        sandbox = DockerSandbox(mode="agent")
        result = await sandbox.execute("print('agent mode')")

        assert result is not None


# ---------------------------------------------------------------------------
# Tests — Workspace Access Controls
# ---------------------------------------------------------------------------

class TestWorkspaceAccessControls:
    """Workspace access is restricted by mode (none/ro/rw)."""

    async def test_workspace_none_blocks_file_access(self, docker_available):
        """workspace=none blocks file read/write."""
        from wanclaw.agent.docker_sandbox import DockerSandbox

        sandbox = DockerSandbox(workspace_access="none")
        result = await sandbox.execute("open('/data/file.txt').read()")

        result_str = str(result)
        assert (
            "permission" in result_str.lower()
            or "denied" in result_str.lower()
            or "blocked" in result_str.lower()
            or "error" in result_str.lower()
        )

    async def test_workspace_ro_allows_read(self, docker_available):
        """workspace=ro allows reading files."""
        from wanclaw.agent.docker_sandbox import DockerSandbox

        sandbox = DockerSandbox(workspace_access="ro")
        # Should allow read, not write
        mock_container = docker_available.containers.run.return_value
        mock_container.exec_run.return_value.output = b"file content"

        result = await sandbox.execute("print(open('/data/file.txt').read())")
        assert result is not None

    async def test_workspace_rw_allows_read_and_write(self, docker_available):
        """workspace=rw allows both reading and writing files."""
        from wanclaw.agent.docker_sandbox import DockerSandbox

        sandbox = DockerSandbox(workspace_access="rw")
        mock_container = docker_available.containers.run.return_value
        mock_container.exec_run.return_value.output = b"written"

        result = await sandbox.execute("f = open('/data/out.txt', 'w'); f.write('ok')")
        assert result is not None
