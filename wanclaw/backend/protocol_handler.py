"""
WanClaw 生态站协议处理器
处理 wanclaw:// 协议，支持从 ClawHub 一键安装插件
"""

import asyncio
import json
import logging
import re
from typing import Dict, Optional, Any
from urllib.parse import urlparse, parse_qs
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ProtocolAction(Enum):
    """协议动作类型"""
    INSTALL = "install"
    UPDATE = "update"
    UNINSTALL = "uninstall"
    ENABLE = "enable"
    DISABLE = "disable"
    OPEN = "open"


@dataclass
class ProtocolRequest:
    """协议请求"""
    action: ProtocolAction
    plugin_id: str
    url: str = ""
    version: str = ""
    checksum: str = ""
    metadata: Dict[str, Any] = None


@dataclass
class ProtocolResult:
    """协议处理结果"""
    success: bool
    message: str
    plugin_id: str = ""
    version: str = ""
    details: Dict[str, Any] = None


class ProtocolHandler:
    """wanclaw:// 协议处理器"""

    def __init__(self, plugin_manager=None, config=None):
        self.plugin_manager = plugin_manager
        self.config = config
        self._pending_installs: Dict[str, ProtocolRequest] = {}
    
    def set_plugin_manager(self, plugin_manager):
        """设置插件管理器"""
        self.plugin_manager = plugin_manager
    
    def set_config(self, config):
        """设置配置"""
        self.config = config
    
    def parse_url(self, url: str) -> Optional[ProtocolRequest]:
        """解析 wanclaw:// URL
        
        支持格式:
        - wanclaw://install?plugin_id=xxx&url=xxx&version=xxx&checksum=xxx
        - wanclaw://update?plugin_id=xxx&url=xxx
        - wanclaw://open?page=marketplace
        """
        try:
            if not url.startswith('wanclaw://'):
                return None
            
            parsed = urlparse(url)
            action_str = parsed.netloc or parsed.path.split('/')[0]
            
            try:
                action = ProtocolAction(action_str)
            except ValueError:
                logger.error(f"Unknown protocol action: {action_str}")
                return None
            
            query_params = parse_qs(parsed.query)
            
            plugin_id = query_params.get('plugin_id', [''])[0]
            download_url = query_params.get('url', [''])[0]
            version = query_params.get('version', [''])[0]
            checksum = query_params.get('checksum', [''])[0]
            
            return ProtocolRequest(
                action=action,
                plugin_id=plugin_id,
                url=download_url,
                version=version,
                checksum=checksum,
                metadata=dict(query_params)
            )
            
        except Exception as e:
            logger.error(f"Failed to parse protocol URL: {e}")
            return None
    
    async def handle(self, request: ProtocolRequest) -> ProtocolResult:
        """处理协议请求"""
        if request.action == ProtocolAction.INSTALL:
            return await self._handle_install(request)
        elif request.action == ProtocolAction.UPDATE:
            return await self._handle_update(request)
        elif request.action == ProtocolAction.UNINSTALL:
            return await self._handle_uninstall(request)
        elif request.action == ProtocolAction.ENABLE:
            return await self._handle_enable(request)
        elif request.action == ProtocolAction.DISABLE:
            return await self._handle_disable(request)
        elif request.action == ProtocolAction.OPEN:
            return await self._handle_open(request)
        else:
            return ProtocolResult(
                success=False,
                message=f"Unknown action: {request.action}"
            )
    
    async def _handle_install(self, request: ProtocolRequest) -> ProtocolResult:
        """处理安装请求"""
        if not self.plugin_manager:
            return ProtocolResult(
                success=False,
                message="Plugin manager not initialized"
            )
        
        if not request.url:
            return ProtocolResult(
                success=False,
                message="Missing download URL"
            )
        
        logger.info(f"Installing plugin from: {request.url}")
        
        try:
            result = await self.plugin_manager.install_from_url(
                url=request.url,
                plugin_id=request.plugin_id
            )
            
            if result.get('success'):
                return ProtocolResult(
                    success=True,
                    message=f"Plugin {request.plugin_id} installed successfully",
                    plugin_id=request.plugin_id,
                    version=result.get('version', ''),
                    details=result
                )
            else:
                return ProtocolResult(
                    success=False,
                    message=result.get('error', 'Installation failed'),
                    plugin_id=request.plugin_id,
                    details=result
                )
                
        except Exception as e:
            logger.error(f"Install failed: {e}")
            return ProtocolResult(
                success=False,
                message=f"Installation error: {str(e)}",
                plugin_id=request.plugin_id
            )
    
    async def _handle_update(self, request: ProtocolRequest) -> ProtocolResult:
        """处理更新请求"""
        if not self.plugin_manager:
            return ProtocolResult(
                success=False,
                message="Plugin manager not initialized"
            )
        
        logger.info(f"Updating plugin: {request.plugin_id}")
        
        try:
            result = await self.plugin_manager.update_plugin(request.plugin_id)
            
            if result.get('success'):
                return ProtocolResult(
                    success=True,
                    message=f"Plugin {request.plugin_id} updated successfully",
                    plugin_id=request.plugin_id,
                    version=result.get('version', ''),
                    details=result
                )
            else:
                return ProtocolResult(
                    success=False,
                    message=result.get('error', 'Update failed'),
                    plugin_id=request.plugin_id
                )
                
        except Exception as e:
            logger.error(f"Update failed: {e}")
            return ProtocolResult(
                success=False,
                message=f"Update error: {str(e)}",
                plugin_id=request.plugin_id
            )
    
    async def _handle_uninstall(self, request: ProtocolRequest) -> ProtocolResult:
        """处理卸载请求"""
        if not self.plugin_manager:
            return ProtocolResult(
                success=False,
                message="Plugin manager not initialized"
            )
        
        logger.info(f"Uninstalling plugin: {request.plugin_id}")
        
        result = self.plugin_manager.uninstall(request.plugin_id)
        
        return ProtocolResult(
            success=result.get('success', False),
            message="Uninstalled" if result.get('success') else result.get('error', 'Uninstall failed'),
            plugin_id=request.plugin_id
        )
    
    async def _handle_enable(self, request: ProtocolRequest) -> ProtocolResult:
        """处理启用请求"""
        if not self.plugin_manager:
            return ProtocolResult(
                success=False,
                message="Plugin manager not initialized"
            )
        
        result = self.plugin_manager.enable(request.plugin_id)
        
        return ProtocolResult(
            success=result.get('success', False),
            message="Enabled" if result.get('success') else result.get('error', 'Enable failed'),
            plugin_id=request.plugin_id
        )
    
    async def _handle_disable(self, request: ProtocolRequest) -> ProtocolResult:
        """处理禁用请求"""
        if not self.plugin_manager:
            return ProtocolResult(
                success=False,
                message="Plugin manager not initialized"
            )
        
        result = self.plugin_manager.disable(request.plugin_id)
        
        return ProtocolResult(
            success=result.get('success', False),
            message="Disabled" if result.get('success') else result.get('error', 'Disable failed'),
            plugin_id=request.plugin_id
        )
    
    async def _handle_open(self, request: ProtocolRequest) -> ProtocolResult:
        """处理打开请求"""
        page = request.metadata.get('page', [''])[0] if request.metadata else ''
        
        return ProtocolResult(
            success=True,
            message=f"Opening page: {page}",
            details={'page': page}
        )
    
    def build_install_url(self, plugin_id: str, download_url: str, version: str = "", checksum: str = "") -> str:
        """构建安装URL
        
        用于前端生成 wanclaw:// 安装链接
        """
        params = [f"plugin_id={plugin_id}", f"url={download_url}"]
        if version:
            params.append(f"version={version}")
        if checksum:
            params.append(f"checksum={checksum}")
        
        return f"wanclaw://install?{'&'.join(params)}"
    
    def get_marketplace_url(self) -> str:
        """获取生态站地址"""
        if self.config:
            return self.config.get("marketplace.url", "http://localhost:5001")
        return "http://localhost:5001"


_protocol_handler: Optional[ProtocolHandler] = None


def get_protocol_handler(**kwargs) -> ProtocolHandler:
    """获取全局协议处理器"""
    global _protocol_handler
    if _protocol_handler is None:
        _protocol_handler = ProtocolHandler(**kwargs)
    return _protocol_handler
