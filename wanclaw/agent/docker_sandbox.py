try:
    import docker as _docker_module
except ImportError:
    _docker_module = None


class _DockerWrapper:
    """Wraps docker module so .from_env() returns the underlying module."""
    def __init__(self, dg):
        self._dg = dg

    def from_env(self):
        return self._dg

    def __getattr__(self, name):
        return getattr(self._dg, name)


if _docker_module is not None:
    _docker_wrapped = _DockerWrapper(_docker_module)
else:
    _docker_wrapped = None

from wanclaw.backend.agent.docker_sandbox import DockerSandbox

docker = _docker_wrapped

__all__ = ["DockerSandbox", "docker"]
