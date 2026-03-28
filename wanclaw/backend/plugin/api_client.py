"""
WanClaw 社区API客户端
对接Claw共生社区云端平台
"""

import os
import json
import logging
import httpx
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_API_BASE = os.environ.get('WANHUB_API_URL', 'https://wanhub.vanyue.cn/api/community')

class CommunityClient:
    """社区API客户端"""
    
    def __init__(self, api_base: str = None):
        self.api_base = (api_base or DEFAULT_API_BASE).rstrip('/')
        self.token = None
        self._load_token()
    
    def _load_token(self):
        """加载本地token"""
        token_path = Path(__file__).parent.parent.parent / 'data' / 'community_token.txt'
        if token_path.exists():
            try:
                self.token = token_path.read_text().strip()
            except Exception:
                pass
    
    def _save_token(self):
        """保存token"""
        token_path = Path(__file__).parent.parent.parent / 'data' / 'community_token.txt'
        token_path.parent.mkdir(parents=True, exist_ok=True)
        if self.token:
            token_path.write_text(self.token)
        elif token_path.exists():
            token_path.unlink()
    
    def _get_headers(self) -> Dict:
        """获取请求头"""
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return headers
    
    async def login(self, username: str, password: str) -> Dict:
        """登录"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f'{self.api_base}/auth/login',
                    json={'username': username, 'password': password}
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    self.token = data.get('token')
                    self._save_token()
                    return {'success': True, 'user': data.get('user')}
                else:
                    return {'success': False, 'error': resp.json().get('error', '登录失败')}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def register(self, username: str, email: str, password: str) -> Dict:
        """注册"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f'{self.api_base}/auth/register',
                    json={'username': username, 'email': email, 'password': password}
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    self.token = data.get('token')
                    self._save_token()
                    return {'success': True, 'user': data.get('user')}
                else:
                    return {'success': False, 'error': resp.json().get('error', '注册失败')}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def logout(self):
        """退出登录"""
        self.token = None
        self._save_token()
    
    async def get_profile(self) -> Dict:
        """获取用户信息"""
        if not self.token:
            return {'success': False, 'error': '未登录'}
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f'{self.api_base}/auth/profile',
                    headers=self._get_headers()
                )
                
                if resp.status_code == 200:
                    return {'success': True, 'user': resp.json().get('user')}
                else:
                    return {'success': False, 'error': '获取用户信息失败'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def get_plugin_list(self, 
                            plugin_type: str = None,
                            category: str = None,
                            search: str = None,
                            page: int = 1,
                            per_page: int = 20) -> Dict:
        """获取插件列表"""
        try:
            params = {'page': page, 'per_page': per_page}
            if plugin_type:
                params['type'] = plugin_type
            if category:
                params['category'] = category
            if search:
                params['search'] = search
            
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f'{self.api_base}/plugins/list',
                    params=params
                )
                
                if resp.status_code == 200:
                    return resp.json()
                else:
                    return {'plugins': [], 'total': 0, 'error': '获取插件列表失败'}
        except Exception as e:
            logger.error(f"Get plugin list failed: {e}")
            return {'plugins': [], 'total': 0, 'error': str(e)}
    
    async def get_plugin_detail(self, plugin_id: str) -> Dict:
        """获取插件详情"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f'{self.api_base}/plugins/detail',
                    params={'plugin_id': plugin_id}
                )
                
                if resp.status_code == 200:
                    return {'success': True, **resp.json()}
                else:
                    return {'success': False, 'error': '获取插件详情失败'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def get_download_url(self, plugin_id: str) -> Dict:
        """获取插件下载地址"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f'{self.api_base}/plugins/download',
                    params={'plugin_id': plugin_id}
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    # 构建完整URL
                    download_url = data.get('download_url', '')
                    if download_url and not download_url.startswith('http'):
                        download_url = f"{self.api_base.replace('/api/community', '')}{download_url}"
                    
                    return {
                        'success': True,
                        'download_url': download_url,
                        'signature': data.get('signature'),
                        'expires_in': data.get('expires_in')
                    }
                else:
                    return {'success': False, 'error': '获取下载地址失败'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def get_comments(self, plugin_id: str, page: int = 1, per_page: int = 20) -> Dict:
        """获取插件评论"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f'{self.api_base}/plugins/comments',
                    params={'plugin_id': plugin_id, 'page': page, 'per_page': per_page}
                )
                
                if resp.status_code == 200:
                    return resp.json()
                else:
                    return {'comments': [], 'total': 0}
        except Exception as e:
            return {'comments': [], 'total': 0, 'error': str(e)}
    
    async def add_comment(self, plugin_id: str, content: str, rating: int = 5) -> Dict:
        """添加评论"""
        if not self.token:
            return {'success': False, 'error': '请先登录'}
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f'{self.api_base}/plugins/comments',
                    headers=self._get_headers(),
                    json={'plugin_id': plugin_id, 'content': content, 'rating': rating}
                )
                
                if resp.status_code == 200:
                    return {'success': True}
                else:
                    return {'success': False, 'error': resp.json().get('error', '评论失败')}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def submit_feedback(self, 
                            content: str,
                            feedback_type: str = 'other',
                            plugin_id: str = None,
                            contact: str = None) -> Dict:
        """提交反馈"""
        try:
            data = {'content': content, 'type': feedback_type}
            if plugin_id:
                data['plugin_id'] = plugin_id
            if contact:
                data['contact'] = contact
            
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f'{self.api_base}/feedback',
                    headers=self._get_headers(),
                    json=data
                )
                
                if resp.status_code == 200:
                    return {'success': True, **resp.json()}
                else:
                    return {'success': False, 'error': '提交反馈失败'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def get_stats(self) -> Dict:
        """获取社区统计"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f'{self.api_base}/stats')
                
                if resp.status_code == 200:
                    return resp.json()
                else:
                    return {'total_plugins': 0, 'total_downloads': 0}
        except Exception as e:
            return {'total_plugins': 0, 'total_downloads': 0, 'error': str(e)}
    
    def is_logged_in(self) -> bool:
        """是否已登录"""
        return self.token is not None


# 全局客户端实例
_community_client: Optional[CommunityClient] = None

def get_community_client(**kwargs) -> CommunityClient:
    """获取全局客户端实例"""
    global _community_client
    if _community_client is None:
        _community_client = CommunityClient(**kwargs)
    return _community_client
