# Thin compatibility shim so tests can import from 'wanclaw.agent.bootstrap_loader'
from wanclaw.backend.agent.bootstrap_loader import (
    BootstrapLoader,
    BootstrapFile,
    BootstrapContext,
    BootstrapConfig,
    BootstrapOrder,
    format_bootstrap_warning,
    get_bootstrap_file_path,
)

__all__ = [
    "BootstrapLoader",
    "BootstrapFile",
    "BootstrapContext",
    "BootstrapConfig",
    "BootstrapOrder",
    "format_bootstrap_warning",
    "get_bootstrap_file_path",
]
