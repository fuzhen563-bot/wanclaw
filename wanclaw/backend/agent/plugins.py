"""
WanClaw Plugin System

Hot-pluggable Python plugins that extend WanClaw's capabilities.
Plugins live in ~/.wanclaw/plugins/<name>/ and export a register(api) function.

Plugin manifest (plugin.json):
{
  "name": "my-plugin",
  "version": "1.0.0",
  "author": "...",
  "description": "...",
  "permissions": ["network", "filesystem:./data"],
  "dependencies": []
}

Plugin file (main.py):
  def register(api: PluginApi):
      api.register_tool(...)
      api.register_hook(...)
"""

import asyncio
import hashlib
import importlib
import importlib.util
import json
import logging
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable

logger = logging.getLogger(__name__)

BLOCKED_IMPORTS = {
    "os": ["system", "popen", "spawn", "fork"],
    "subprocess": ["Popen", "call", "run", "spawn"],
    "socket": ["create_connection", "socket"],
    "urllib": ["urlopen", "urlretrieve"],
    "requests": ["get", "post", "put", "delete"],
    "http": ["client"],
    "pty": [],
    "tty": [],
    "fcntl": [],
    "resource": [],
    "prctl": [],
}


class PluginApi:
    """
    The api object passed to every plugin's register() function.
    Provides access to WanClaw's core capabilities in a controlled way.
    """

    def __init__(self, manager: "PluginManager"):
        self._mgr = manager
        self._tools: Dict[str, Any] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        self._gateway_hooks: Dict[str, List[Callable]] = {}
        self._skills: List[Dict] = []
        self._name = ""
        self._config: Dict = {}

    def set_plugin_name(self, name: str):
        self._name = name

    def set_config(self, config: Dict):
        self._config = config

    def log(self, level: str, msg: str):
        getattr(logger, level.lower(), logger.info)(f"[plugin:{self._name}] {msg}")

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict,
        handler: Callable,
        requires_confirm: bool = False,
    ):
        from wanclaw.backend.agent.core import Tool
        tool = Tool(
            name=f"{self._name}_{name}" if self._name else name,
            description=description,
            parameters=parameters,
            handler=handler,
            requires_confirm=requires_confirm,
        )
        self._tools[tool.name] = tool
        self._mgr._register_tool(tool)
        self.log("info", f"Tool registered: {tool.name}")

    def register_hook(self, event: str, handler: Callable, priority: int = 100, blocking: bool = False):
        self._mgr.register_plugin_hook(self._name, event, handler, priority, blocking)
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(handler)
        self.log("info", f"Hook registered: {event}")

    def register_gateway_hook(self, command: str, handler: Callable, priority: int = 100):
        self._mgr.register_plugin_gateway_hook(self._name, command, handler, priority)

    def register_skill(self, name: str, description: str, handler: Callable, tags: List[str] = None):
        self._skills.append({
            "name": name,
            "description": description,
            "handler": handler,
            "tags": tags or [],
            "plugin": self._name,
        })
        self.log("info", f"Skill registered: {name}")

    def get_config(self, key: str, default: Any = None) -> Any:
        return self._mgr.get_plugin_config(self._name, key, default)

    def get_workspace_path(self) -> str:
        base = os.path.expanduser("~/.wanclaw/plugins")
        return os.path.join(base, self._name)


class Plugin:
    def __init__(self, name: str, path: Path, manifest: Dict):
        self.name = name
        self.path = path
        self.manifest = manifest
        self.version = manifest.get("version", "0.0.0")
        self.author = manifest.get("author", "")
        self.description = manifest.get("description", "")
        self.permissions: List[str] = manifest.get("permissions", [])
        self.enabled = True
        self.loaded = False
        self.api: Optional[PluginApi] = None
        self._module = None
        self._mtime = 0.0
        self._tools: Dict[str, Any] = {}
        self._registered_hooks: Dict[str, List[Callable]] = {}
        self._registered_gateway_hooks: Dict[str, List[Callable]] = {}

    def _check_permissions(self) -> bool:
        for perm in self.permissions:
            if perm == "*":
                return True
        return True

    def load(self) -> bool:
        if self.loaded:
            return True
        main_py = self.path / "main.py"
        if not main_py.exists():
            logger.error(f"Plugin {self.name}: main.py not found")
            return False

        self.api = PluginApi(self._mgr)
        self.api.set_plugin_name(self.name)
        try:
            spec = importlib.util.spec_from_file_location(f"wanclaw_plugin_{self.name}", str(main_py))
            if spec is None or spec.loader is None:
                logger.error(f"Plugin {self.name}: failed to load spec")
                return False
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"wanclaw_plugin_{self.name}"] = module
            spec.loader.exec_module(module)
            if hasattr(module, "register"):
                self._module = module
                module.register(self.api)
                self.loaded = True
                self._mtime = main_py.stat().st_mtime
                logger.info(f"Plugin {self.name} loaded successfully")
                return True
            else:
                logger.error(f"Plugin {self.name}: no register() function found")
                return False
        except Exception as e:
            logger.error(f"Plugin {self.name} load error: {e}\n{traceback.format_exc()}")
            return False

    def unload(self):
        if not self.loaded:
            return
        for event, handlers in list(self._registered_hooks.items()):
            for h in handlers:
                self._mgr.unregister_plugin_hook(self.name, event, h)
        for cmd, handlers in list(self._registered_gateway_hooks.items()):
            for h in handlers:
                pass
        self.loaded = False
        self._module = None
        logger.info(f"Plugin {self.name} unloaded")

    def reload(self) -> bool:
        self.unload()
        return self.load()

    def check_updated(self) -> bool:
        main_py = self.path / "main.py"
        if main_py.exists() and main_py.stat().st_mtime > self._mtime:
            return True
        return False


class PluginManager:
    """
    Manages the lifecycle of all plugins: discovery, loading, hot-reload, unloading.
    Plugins live in ~/.wanclaw/plugins/<name>/ with a plugin.json manifest.
    """

    def __init__(self, plugins_dir: str = None):
        self._plugins_dir = Path(plugins_dir or os.path.expanduser("~/.wanclaw/plugins"))
        self._plugins: Dict[str, Plugin] = {}
        self._tools: Dict[str, Any] = {}
        self._hook_manager = None
        self._agent_core = None
        self._skill_manager = None
        self._running = False
        self._watch_tasks: List[asyncio.Task] = []
        self._file_timestamps: Dict[str, float] = {}

    def set_hook_manager(self, hm):
        self._hook_manager = hm

    def set_agent_core(self, core):
        self._agent_core = core

    def set_skill_manager(self, sm):
        self._skill_manager = sm

    def get_plugins_dir(self) -> Path:
        self._plugins_dir.mkdir(parents=True, exist_ok=True)
        return self._plugins_dir

    def discover_plugins(self) -> List[Dict]:
        self.get_plugins_dir()
        found = []
        for entry in self._plugins_dir.iterdir():
            if not entry.is_dir():
                continue
            manifest_path = entry / "plugin.json"
            if not manifest_path.exists():
                continue
            try:
                manifest = json.loads(manifest_path.read_text())
                manifest["name"] = entry.name
                manifest["path"] = str(entry)
                manifest["loaded"] = entry.name in self._plugins and self._plugins[entry.name].loaded
                found.append(manifest)
            except Exception as e:
                logger.warning(f"Plugin manifest error in {entry}: {e}")
        return found

    def load_plugin(self, name: str) -> bool:
        if name in self._plugins and self._plugins[name].loaded:
            return True
        plugin_path = self._plugins_dir / name
        manifest_path = plugin_path / "plugin.json"
        if not manifest_path.exists():
            logger.error(f"Plugin {name}: not found")
            return False
        try:
            manifest = json.loads(manifest_path.read_text())
        except Exception as e:
            logger.error(f"Plugin {name}: manifest parse error: {e}")
            return False
        plugin = Plugin(name, plugin_path, manifest)
        plugin._mgr = self
        if plugin.load():
            self._plugins[name] = plugin
            return True
        return False

    def unload_plugin(self, name: str) -> bool:
        if name not in self._plugins:
            return False
        self._plugins[name].unload()
        del self._plugins[name]
        return True

    def reload_plugin(self, name: str) -> bool:
        if name not in self._plugins:
            return self.load_plugin(name)
        return self._plugins[name].reload()

    def enable_plugin(self, name: str):
        if name in self._plugins:
            self._plugins[name].enabled = True

    def disable_plugin(self, name: str):
        if name in self._plugins:
            self._plugins[name].enabled = False

    def install_plugin(self, source_path: str) -> bool:
        name = Path(source_path).name
        dest = self._plugins_dir / name
        if dest.exists():
            logger.error(f"Plugin {name} already installed")
            return False
        import shutil
        try:
            shutil.copytree(source_path, dest)
            logger.info(f"Plugin {name} installed to {dest}")
            return self.load_plugin(name)
        except Exception as e:
            logger.error(f"Plugin {name} install failed: {e}")
            return False

    def uninstall_plugin(self, name: str) -> bool:
        self.unload_plugin(name)
        import shutil
        dest = self._plugins_dir / name
        if dest.exists():
            shutil.rmtree(dest)
            logger.info(f"Plugin {name} uninstalled")
            return True
        return False

    def _register_tool(self, tool):
        self._tools[tool.name] = tool
        if self._agent_core:
            self._agent_core.register_tool(tool)

    def register_plugin_hook(self, plugin_name: str, event: str, handler: Callable, priority: int, blocking: bool):
        if self._hook_manager:
            self._hook_manager.register(event, handler, priority, blocking)
            if plugin_name not in [p.name for p in self._plugins.values()]:
                return
            for p in self._plugins.values():
                if p.name == plugin_name:
                    if event not in p._registered_hooks:
                        p._registered_hooks[event] = []
                    p._registered_hooks[event].append(handler)
                    break

    def register_plugin_gateway_hook(self, plugin_name: str, command: str, handler: Callable, priority: int):
        if self._hook_manager:
            self._hook_manager.register_gateway_hook(command, handler, priority)
            for p in self._plugins.values():
                if p.name == plugin_name:
                    if command not in p._registered_gateway_hooks:
                        p._registered_gateway_hooks[command] = []
                    p._registered_gateway_hooks[command].append(handler)
                    break

    def unregister_plugin_hook(self, plugin_name: str, event: str, handler: Callable):
        if self._hook_manager:
            self._hook_manager.unregister(event, handler)

    def get_plugin_config(self, plugin_name: str, key: str, default: Any = None) -> Any:
        if plugin_name in self._plugins:
            return self._plugins[plugin_name].manifest.get(key, default)
        return default

    def get_all_tools(self) -> Dict[str, Any]:
        return dict(self._tools)

    def get_stats(self) -> Dict:
        return {
            "plugins_dir": str(self._plugins_dir),
            "loaded": [p for p in self._plugins.values() if p.loaded],
            "total_tools": len(self._tools),
            "hot_reload_enabled": self._running,
        }

    async def _watch_loop(self):
        while self._running:
            try:
                for name, plugin in list(self._plugins.items()):
                    if not plugin.enabled:
                        continue
                    if plugin.check_updated():
                        logger.info(f"Hot-reloading plugin: {name}")
                        plugin.reload()
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Plugin watch loop error: {e}")

    def start_hot_reload(self):
        if not self._running:
            self._running = True
            task = asyncio.create_task(self._watch_loop())
            self._watch_tasks.append(task)
            logger.info("Plugin hot-reload started")

    def stop_hot_reload(self):
        self._running = False
        for t in self._watch_tasks:
            t.cancel()
        self._watch_tasks.clear()
        logger.info("Plugin hot-reload stopped")

    def load_all(self):
        for entry in self.discover_plugins():
            name = entry["name"]
            if name not in self._plugins:
                self.load_plugin(name)


_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
        _plugin_manager.set_hook_manager(None)
    return _plugin_manager


def reset_plugin_manager():
    global _plugin_manager
    if _plugin_manager:
        _plugin_manager.stop_hot_reload()
    _plugin_manager = None
