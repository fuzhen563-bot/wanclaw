"""
WanClaw 插件管理器
整合加载器、安全模块，提供完整的插件管理功能
"""

import os
import json
import shutil
import zipfile
import tempfile
import logging
import asyncio
import httpx
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from .loader import PluginLoader, PluginStatus, get_plugin_loader
from .security import PluginSecurity, get_plugin_security, RiskLevel

logger = logging.getLogger(__name__)

class PluginManager:
    """插件管理器"""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or os.path.dirname(__file__))
        self.loader = get_plugin_loader(plugin_dir=str(self.base_dir / '..' / '..' / 'plugins'))
        self.security = get_plugin_security()
        self.registry_path = self.base_dir / 'registry.json'
        self.registry: Dict[str, Dict] = {}
        self._load_registry()
    
    def _load_registry(self):
        """加载注册表"""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, 'r', encoding='utf-8') as f:
                    self.registry = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load registry: {e}")
                self.registry = {}
    
    def _save_registry(self):
        """保存注册表"""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_path, 'w', encoding='utf-8') as f:
            json.dump(self.registry, f, indent=2, ensure_ascii=False)
    
    async def install_from_url(self, url: str, plugin_id: str = None) -> Dict:
        """从URL下载并安装插件"""
        try:
            tmp_dir = tempfile.mkdtemp(prefix='wanclaw_plugin_')
            zip_path = os.path.join(tmp_dir, 'plugin.zip')
            
            # 下载
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return {'success': False, 'error': f'下载失败: {resp.status_code}'}
                
                with open(zip_path, 'wb') as f:
                    f.write(resp.content)
            
            # 安全扫描
            report = self.security.scan_plugin_zip(zip_path)
            if not report.safe:
                return {
                    'success': False,
                    'error': '安全扫描未通过',
                    'risk_level': report.risk_level.value,
                    'warnings': report.warnings,
                    'errors': report.errors
                }
            
            # 安装
            result = self.install_from_zip(zip_path, plugin_id)
            
            # 清理
            shutil.rmtree(tmp_dir, ignore_errors=True)
            
            return result
            
        except Exception as e:
            logger.error(f"Install from URL failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def install_from_zip(self, zip_path: str, plugin_id: str = None) -> Dict:
        """从ZIP文件安装插件"""
        try:
            if not zipfile.is_zipfile(zip_path):
                return {'success': False, 'error': '无效的ZIP文件'}
            
            # 安全扫描（安装前必须通过）
            scan_result = self.scan_plugin(zip_path)
            if not scan_result.get('safe', False):
                risk_level = scan_result.get('risk_level', 'unknown')
                errors = scan_result.get('errors', [])
                warnings = scan_result.get('warnings', [])
                error_msg = f"安全扫描未通过，风险等级: {risk_level}"
                if errors:
                    error_msg += f"，错误: {'; '.join(errors[:3])}"
                return {
                    'success': False,
                    'error': error_msg,
                    'risk_level': risk_level,
                    'errors': errors,
                    'warnings': warnings,
                }
            
            # 解压到临时目录
            tmp_dir = tempfile.mkdtemp(prefix='wanclaw_extract_')
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(tmp_dir)
            
            # 查找plugin.json
            manifest_path = None
            for root, dirs, files in os.walk(tmp_dir):
                if 'plugin.json' in files:
                    manifest_path = os.path.join(root, 'plugin.json')
                    break
            
            if not manifest_path:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                return {'success': False, 'error': '缺少plugin.json文件'}
            
            # 读取清单
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            plugin_id = plugin_id or manifest.get('plugin_id', '')
            if not plugin_id:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                return {'success': False, 'error': '缺少plugin_id'}
            
            # 检查版本兼容性
            compatible = manifest.get('compatible_wanclaw_version', '*')
            is_compatible, compat_msg = self.security.check_version_compatibility(compatible)
            if not is_compatible:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                return {'success': False, 'error': f'版本不兼容: {compat_msg}'}
            
            # 确定安装目录
            plugin_type = manifest.get('plugin_type', 'skill')
            type_dirs = {
                'skill': 'skills',
                'adapter': 'adapters',
                'workflow': 'workflows',
                'prompt': 'prompts'
            }
            type_dir = type_dirs.get(plugin_type, 'skills')
            install_dir = self.loader.plugin_dir / type_dir / plugin_id
            
            # 删除旧版本
            if install_dir.exists():
                shutil.rmtree(install_dir)
            
            # 复制文件
            extract_root = Path(manifest_path).parent
            shutil.copytree(str(extract_root), str(install_dir))
            
            # 更新注册表
            self.registry[plugin_id] = {
                'plugin_id': plugin_id,
                'name': manifest.get('plugin_name', plugin_id),
                'version': manifest.get('version', '1.0.0'),
                'plugin_type': plugin_type,
                'category': manifest.get('category', 'custom'),
                'install_path': str(install_dir),
                'installed_at': datetime.utcnow().isoformat(),
                'manifest': manifest,
            }
            self._save_registry()
            
            # 重新发现插件并加载
            self.loader.discover_plugins()
            load_success = self.loader.load_plugin(plugin_id)
            
            # 清理
            shutil.rmtree(tmp_dir, ignore_errors=True)
            
            return {
                'success': True,
                'plugin_id': plugin_id,
                'version': manifest.get('version', '1.0.0'),
                'loaded': load_success,
                'compatibility': compat_msg
            }
            
        except Exception as e:
            logger.error(f"Install from ZIP failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def uninstall(self, plugin_id: str) -> Dict:
        """卸载插件"""
        try:
            # 卸载模块
            self.loader.unload_plugin(plugin_id)
            
            # 删除文件
            plugin_info = self.loader.plugins.get(plugin_id)
            if plugin_info and plugin_info.install_path:
                install_path = Path(plugin_info.install_path)
                if install_path.exists():
                    shutil.rmtree(install_path)
            
            # 从注册表删除
            if plugin_id in self.registry:
                del self.registry[plugin_id]
                self._save_registry()
            
            # 从加载器删除
            if plugin_id in self.loader.plugins:
                del self.loader.plugins[plugin_id]
            
            logger.info(f"Plugin uninstalled: {plugin_id}")
            return {'success': True, 'plugin_id': plugin_id}
            
        except Exception as e:
            logger.error(f"Uninstall failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def enable(self, plugin_id: str) -> Dict:
        """启用插件"""
        plugin_info = self.loader.plugins.get(plugin_id)
        if not plugin_info:
            return {'success': False, 'error': '插件不存在'}
        
        success = self.loader.load_plugin(plugin_id)
        
        if plugin_id in self.registry:
            self.registry[plugin_id]['enabled'] = True
            self._save_registry()
        
        return {'success': success, 'plugin_id': plugin_id}
    
    def disable(self, plugin_id: str) -> Dict:
        """禁用插件"""
        success = self.loader.unload_plugin(plugin_id)
        
        if plugin_id in self.registry:
            self.registry[plugin_id]['enabled'] = False
            self._save_registry()
        
        return {'success': success, 'plugin_id': plugin_id}
    
    def reload(self, plugin_id: str) -> Dict:
        """重载插件"""
        success = self.loader.reload_plugin(plugin_id)
        return {'success': success, 'plugin_id': plugin_id}
    
    def get_plugin_info(self, plugin_id: str) -> Optional[Dict]:
        """获取插件详细信息"""
        plugin_info = self.loader.plugins.get(plugin_id)
        registry_info = self.registry.get(plugin_id, {})
        
        if not plugin_info:
            return None
        
        return {
            'plugin_id': plugin_info.plugin_id,
            'name': plugin_info.name,
            'version': plugin_info.version,
            'plugin_type': plugin_info.plugin_type,
            'category': plugin_info.category,
            'description': plugin_info.description,
            'author': plugin_info.author,
            'permissions': plugin_info.permissions,
            'status': plugin_info.status.value,
            'error_message': plugin_info.error_message,
            'install_path': plugin_info.install_path,
            'installed_at': registry_info.get('installed_at'),
            'enabled': registry_info.get('enabled', True),
        }
    
    def list_plugins(self, plugin_type: str = None, status: str = None) -> List[Dict]:
        """列出所有插件"""
        plugins = []
        for plugin_id, plugin_info in self.loader.plugins.items():
            if plugin_type and plugin_info.plugin_type != plugin_type:
                continue
            if status and plugin_info.status.value != status:
                continue
            
            info = self.get_plugin_info(plugin_id)
            if info:
                plugins.append(info)
        
        return sorted(plugins, key=lambda x: x.get('installed_at', ''), reverse=True)
    
    async def check_updates(self) -> List[Dict]:
        """检查插件更新"""
        updates = []
        
        for plugin_id, registry_info in self.registry.items():
            remote_url = registry_info.get('manifest', {}).get('update_url')
            if not remote_url:
                continue
            
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(remote_url)
                    if resp.status_code == 200:
                        remote_info = resp.json()
                        local_version = registry_info.get('version', '0.0.0')
                        remote_version = remote_info.get('version', '0.0.0')
                        
                        if remote_version > local_version:
                            updates.append({
                                'plugin_id': plugin_id,
                                'local_version': local_version,
                                'remote_version': remote_version,
                                'update_url': remote_info.get('download_url'),
                                'changelog': remote_info.get('changelog', ''),
                            })
            except Exception as e:
                logger.warning(f"Check update failed for {plugin_id}: {e}")
        
        return updates
    
    async def update_plugin(self, plugin_id: str) -> Dict:
        """更新插件"""
        updates = await self.check_updates()
        update_info = next((u for u in updates if u['plugin_id'] == plugin_id), None)
        
        if not update_info:
            return {'success': False, 'error': '没有可用更新'}
        
        if not update_info.get('update_url'):
            return {'success': False, 'error': '缺少下载地址'}
        
        # 卸载旧版本
        self.uninstall(plugin_id)
        
        # 安装新版本
        return await self.install_from_url(update_info['update_url'], plugin_id)
    
    def scan_plugin(self, zip_path: str) -> Dict:
        """扫描插件安全性"""
        report = self.security.scan_plugin_zip(zip_path)
        return {
            'safe': report.safe,
            'risk_level': report.risk_level.value,
            'warnings': report.warnings,
            'errors': report.errors,
            'permissions_allowed': report.permissions_allowed,
            'permissions_denied': report.permissions_denied,
        }
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        loader_stats = self.loader.get_stats()
        
        return {
            **loader_stats,
            'registry_count': len(self.registry),
        }


# 全局管理器实例
_plugin_manager: Optional[PluginManager] = None

def get_plugin_manager(**kwargs) -> PluginManager:
    """获取全局管理器实例"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager(**kwargs)
    return _plugin_manager
