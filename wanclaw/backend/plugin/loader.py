"""
WanClaw 插件热加载模块
支持动态加载、卸载、重载插件，无需重启服务
"""

import os
import sys
import json
import importlib
import importlib.util
import logging
import asyncio
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class PluginStatus(Enum):
    """插件状态"""
    LOADED = "loaded"
    UNLOADED = "unloaded"
    ERROR = "error"
    LOADING = "loading"

@dataclass
class PluginInfo:
    """插件信息"""
    plugin_id: str
    name: str
    version: str
    plugin_type: str  # skill/adapter/workflow/prompt
    category: str
    description: str = ""
    author: str = ""
    entry_file: str = "main.py"
    permissions: List[str] = field(default_factory=list)
    install_path: str = ""
    status: PluginStatus = PluginStatus.UNLOADED
    module: Any = None
    last_modified: float = 0
    file_hash: str = ""
    error_message: str = ""

class PluginLoader:
    """插件热加载器"""
    
    def __init__(self, plugin_dir: str = None):
        self.plugin_dir = Path(plugin_dir or os.path.join(os.path.dirname(__file__), '..', '..', 'plugins'))
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        self.plugins: Dict[str, PluginInfo] = {}
        self.watch_interval = 5  # 秒
        self._watch_task = None
        self._callbacks: Dict[str, List[Callable]] = {
            'on_load': [],
            'on_unload': [],
            'on_reload': [],
            'on_error': [],
        }
    
    def register_callback(self, event: str, callback: Callable):
        """注册事件回调"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def _fire_event(self, event: str, plugin_info: PluginInfo):
        """触发事件"""
        for callback in self._callbacks.get(event, []):
            try:
                callback(plugin_info)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")
    
    def _calculate_hash(self, file_path: str) -> str:
        """计算文件哈希"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return ""
    
    def _get_plugin_dirs(self) -> List[Path]:
        """获取所有插件目录"""
        plugin_dirs = []
        # 扫描所有类型目录
        for type_dir in ['skills', 'adapters', 'workflows', 'prompts']:
            type_path = self.plugin_dir / type_dir
            if type_path.exists():
                for item in type_path.iterdir():
                    if item.is_dir() and (item / 'plugin.json').exists():
                        plugin_dirs.append(item)
        # 也扫描根目录下的插件
        for item in self.plugin_dir.iterdir():
            if item.is_dir() and (item / 'plugin.json').exists():
                if item not in plugin_dirs:
                    plugin_dirs.append(item)
        return plugin_dirs
    
    def _load_manifest(self, plugin_path: Path) -> Optional[Dict]:
        """加载插件清单"""
        manifest_path = plugin_path / 'plugin.json'
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load manifest from {manifest_path}: {e}")
            return None
    
    def discover_plugins(self) -> List[PluginInfo]:
        """发现所有插件"""
        discovered = []
        for plugin_path in self._get_plugin_dirs():
            manifest = self._load_manifest(plugin_path)
            if manifest:
                plugin_id = manifest.get('plugin_id', plugin_path.name)
                info = PluginInfo(
                    plugin_id=plugin_id,
                    name=manifest.get('plugin_name', plugin_path.name),
                    version=manifest.get('version', '1.0.0'),
                    plugin_type=manifest.get('plugin_type', 'skill'),
                    category=manifest.get('category', 'custom'),
                    description=manifest.get('description', ''),
                    author=manifest.get('author', ''),
                    entry_file=manifest.get('entry_file', 'main.py'),
                    permissions=manifest.get('permissions', []),
                    install_path=str(plugin_path),
                    last_modified=os.path.getmtime(plugin_path / manifest.get('entry_file', 'main.py'))
                        if (plugin_path / manifest.get('entry_file', 'main.py')).exists() else 0,
                )
                discovered.append(info)
                self.plugins[plugin_id] = info
        return discovered
    
    def load_plugin(self, plugin_id: str, force_reload: bool = False) -> bool:
        """加载单个插件"""
        plugin_info = self.plugins.get(plugin_id)
        if not plugin_info:
            logger.error(f"Plugin not found: {plugin_id}")
            return False
        
        if plugin_info.status == PluginStatus.LOADED and not force_reload:
            logger.info(f"Plugin already loaded: {plugin_id}")
            return True
        
        plugin_info.status = PluginStatus.LOADING
        
        try:
            plugin_path = Path(plugin_info.install_path)
            entry_file = plugin_path / plugin_info.entry_file
            
            if not entry_file.exists():
                raise FileNotFoundError(f"Entry file not found: {entry_file}")
            
            # 计算文件哈希
            plugin_info.file_hash = self._calculate_hash(str(entry_file))
            
            # 如果已加载且强制重载，先卸载
            if plugin_info.module is not None and force_reload:
                self.unload_plugin(plugin_id)
            
            # 动态导入模块
            spec = importlib.util.spec_from_file_location(
                f"wanclaw_plugin_{plugin_id.replace('.', '_')}",
                str(entry_file)
            )
            
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot load module spec from {entry_file}")
            
            module = importlib.util.module_from_spec(spec)
            
            # 将插件目录加入sys.path以便导入本地依赖
            if str(plugin_path) not in sys.path:
                sys.path.insert(0, str(plugin_path))
            
            try:
                spec.loader.exec_module(module)
            finally:
                if str(plugin_path) in sys.path:
                    sys.path.remove(str(plugin_path))
            
            plugin_info.module = module
            plugin_info.status = PluginStatus.LOADED
            plugin_info.error_message = ""
            plugin_info.last_modified = os.path.getmtime(entry_file)
            
            logger.info(f"Plugin loaded: {plugin_id} v{plugin_info.version}")
            self._fire_event('on_load', plugin_info)
            return True
            
        except Exception as e:
            plugin_info.status = PluginStatus.ERROR
            plugin_info.error_message = str(e)
            logger.error(f"Failed to load plugin {plugin_id}: {e}")
            self._fire_event('on_error', plugin_info)
            return False
    
    def unload_plugin(self, plugin_id: str) -> bool:
        """卸载插件"""
        plugin_info = self.plugins.get(plugin_id)
        if not plugin_info:
            return False
        
        if plugin_info.status != PluginStatus.LOADED:
            return True
        
        try:
            # 调用插件的cleanup函数（如果有）
            if plugin_info.module and hasattr(plugin_info.module, 'cleanup'):
                try:
                    result = plugin_info.module.cleanup()
                    if asyncio.iscoroutine(result):
                        asyncio.create_task(result)
                except Exception as e:
                    logger.warning(f"Plugin cleanup error for {plugin_id}: {e}")
            
            # 移除模块
            module_name = f"wanclaw_plugin_{plugin_id.replace('.', '_')}"
            if module_name in sys.modules:
                del sys.modules[module_name]
            
            plugin_info.module = None
            plugin_info.status = PluginStatus.UNLOADED
            
            logger.info(f"Plugin unloaded: {plugin_id}")
            self._fire_event('on_unload', plugin_info)
            return True
            
        except Exception as e:
            logger.error(f"Failed to unload plugin {plugin_id}: {e}")
            return False
    
    def reload_plugin(self, plugin_id: str) -> bool:
        """重载插件"""
        if self.unload_plugin(plugin_id):
            if self.load_plugin(plugin_id, force_reload=True):
                plugin_info = self.plugins.get(plugin_id)
                self._fire_event('on_reload', plugin_info)
                return True
        return False
    
    def load_all(self) -> Dict[str, bool]:
        """加载所有插件"""
        results = {}
        self.discover_plugins()
        for plugin_id in self.plugins:
            results[plugin_id] = self.load_plugin(plugin_id)
        return results
    
    def unload_all(self) -> Dict[str, bool]:
        """卸载所有插件"""
        results = {}
        for plugin_id in list(self.plugins.keys()):
            results[plugin_id] = self.unload_plugin(plugin_id)
        return results
    
    def get_plugin(self, plugin_id: str) -> Optional[PluginInfo]:
        """获取插件信息"""
        return self.plugins.get(plugin_id)
    
    def get_loaded_plugins(self) -> List[PluginInfo]:
        """获取已加载的插件列表"""
        return [p for p in self.plugins.values() if p.status == PluginStatus.LOADED]
    
    def get_plugins_by_type(self, plugin_type: str) -> List[PluginInfo]:
        """按类型获取插件"""
        return [p for p in self.plugins.values() if p.plugin_type == plugin_type]
    
    async def execute_plugin(self, plugin_id: str, method: str = 'run', **kwargs) -> Any:
        """执行插件方法"""
        plugin_info = self.plugins.get(plugin_id)
        if not plugin_info or plugin_info.status != PluginStatus.LOADED:
            raise RuntimeError(f"Plugin not loaded: {plugin_id}")
        
        if not plugin_info.module or not hasattr(plugin_info.module, method):
            raise AttributeError(f"Plugin {plugin_id} has no method: {method}")
        
        func = getattr(plugin_info.module, method)
        
        if asyncio.iscoroutinefunction(func):
            return await func(**kwargs)
        else:
            return func(**kwargs)
    
    async def start_watch(self):
        """启动文件监听（检测插件变化自动重载）"""
        if self._watch_task is not None:
            return
        
        async def watch_loop():
            while True:
                await asyncio.sleep(self.watch_interval)
                for plugin_id, plugin_info in self.plugins.items():
                    if plugin_info.status == PluginStatus.LOADED:
                        entry_file = Path(plugin_info.install_path) / plugin_info.entry_file
                        if entry_file.exists():
                            current_hash = self._calculate_hash(str(entry_file))
                            if current_hash != plugin_info.file_hash:
                                logger.info(f"Plugin file changed, reloading: {plugin_id}")
                                self.reload_plugin(plugin_id)
        
        self._watch_task = asyncio.create_task(watch_loop())
        logger.info("Plugin file watcher started")
    
    async def stop_watch(self):
        """停止文件监听"""
        if self._watch_task:
            self._watch_task.cancel()
            self._watch_task = None
            logger.info("Plugin file watcher stopped")
    
    def get_stats(self) -> Dict:
        """获取插件统计"""
        total = len(self.plugins)
        loaded = sum(1 for p in self.plugins.values() if p.status == PluginStatus.LOADED)
        error = sum(1 for p in self.plugins.values() if p.status == PluginStatus.ERROR)
        
        type_counts = {}
        for p in self.plugins.values():
            type_counts[p.plugin_type] = type_counts.get(p.plugin_type, 0) + 1
        
        return {
            'total': total,
            'loaded': loaded,
            'error': error,
            'unloaded': total - loaded - error,
            'types': type_counts,
        }


# 全局插件加载器实例
_plugin_loader: Optional[PluginLoader] = None

def get_plugin_loader(**kwargs) -> PluginLoader:
    """获取全局插件加载器实例"""
    global _plugin_loader
    if _plugin_loader is None:
        _plugin_loader = PluginLoader(**kwargs)
    return _plugin_loader
