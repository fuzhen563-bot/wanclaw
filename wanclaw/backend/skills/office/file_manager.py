"""
文件管理技能
提供文件操作相关功能
"""

import os
import shutil
import pathlib
import hashlib
import mimetypes
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import aiofiles

from wanclaw.backend.skills import BaseSkill, SkillResult, SkillCategory, SkillLevel
from wanclaw.backend.im_adapter.security import get_security, OperationType


logger = logging.getLogger(__name__)


class FileManagerSkill(BaseSkill):
    """文件管理技能"""
    
    def __init__(self):
        super().__init__()
        self.name = "FileManager"
        self.description = "文件管理：列表、复制、移动、删除、查看文件信息"
        self.category = SkillCategory.OFFICE
        self.level = SkillLevel.BEGINNER
        
        # 必需参数
        self.required_params = ["action"]
        
        # 可选参数及其类型
        self.optional_params = {
            "path": str,
            "source": str,
            "destination": str,
            "recursive": bool,
            "show_hidden": bool,
            "pattern": str,
            "max_results": int
        }
    
    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        """
        执行文件管理操作
        
        Args:
            params: {
                "action": "list|info|copy|move|delete|search|hash|size",
                "path": "文件路径",
                "source": "源文件路径",
                "destination": "目标路径",
                "recursive": bool,
                "show_hidden": bool,
                "pattern": "搜索模式",
                "max_results": int
            }
            
        Returns:
            执行结果
        """
        action = params.get("action", "").lower()
        user_id = params.get("user_id", "unknown")
        username = params.get("username", "unknown")
        
        # 安全检查
        security = get_security()
        
        if action in ["list", "info", "search", "hash", "size"]:
            # 读取操作
            path = params.get("path", ".")
            allowed, reason = security.check_file_access(
                path, OperationType.FILE_READ, user_id, username
            )
            if not allowed:
                return SkillResult(
                    success=False,
                    message=f"文件访问被拒绝: {reason}",
                    error="Security check failed"
                )
        elif action in ["copy", "move"]:
            # 写入操作
            source = params.get("source", "")
            destination = params.get("destination", "")
            
            # 检查源文件读取权限
            allowed, reason = security.check_file_access(
                source, OperationType.FILE_READ, user_id, username
            )
            if not allowed:
                return SkillResult(
                    success=False,
                    message=f"源文件访问被拒绝: {reason}",
                    error="Security check failed for source"
                )
            
            # 检查目标文件写入权限
            allowed, reason = security.check_file_access(
                destination, OperationType.FILE_WRITE, user_id, username
            )
            if not allowed:
                return SkillResult(
                    success=False,
                    message=f"目标文件访问被拒绝: {reason}",
                    error="Security check failed for destination"
                )
        elif action == "delete":
            # 删除操作
            path = params.get("path", "")
            allowed, reason = security.check_file_access(
                path, OperationType.FILE_DELETE, user_id, username
            )
            if not allowed:
                return SkillResult(
                    success=False,
                    message=f"文件删除被拒绝: {reason}",
                    error="Security check failed"
                )
        else:
            return SkillResult(
                success=False,
                message=f"不支持的操作: {action}",
                error=f"Unsupported action: {action}"
            )
        
        # 执行具体操作
        try:
            if action == "list":
                return await self._list_files(params)
            elif action == "info":
                return await self._file_info(params)
            elif action == "copy":
                return await self._copy_file(params)
            elif action == "move":
                return await self._move_file(params)
            elif action == "delete":
                return await self._delete_file(params)
            elif action == "search":
                return await self._search_files(params)
            elif action == "hash":
                return await self._file_hash(params)
            elif action == "size":
                return await self._file_size(params)
            else:
                return SkillResult(
                    success=False,
                    message=f"未知操作: {action}",
                    error="Unknown action"
                )
        except Exception as e:
            logger.error(f"文件操作失败: {action} - {e}")
            return SkillResult(
                success=False,
                message=f"文件操作失败: {str(e)}",
                error=str(e)
            )
    
    async def _list_files(self, params: Dict[str, Any]) -> SkillResult:
        """列出目录内容"""
        path = params.get("path", ".")
        recursive = params.get("recursive", False)
        show_hidden = params.get("show_hidden", False)
        
        if not os.path.exists(path):
            return SkillResult(
                success=False,
                message=f"路径不存在: {path}",
                error="Path not found"
            )
        
        if not os.path.isdir(path):
            return SkillResult(
                success=False,
                message=f"不是目录: {path}",
                error="Not a directory"
            )
        
        files = []
        total_size = 0
        file_count = 0
        dir_count = 0
        
        if recursive:
            for root, dirs, filenames in os.walk(path):
                # 过滤隐藏文件
                if not show_hidden:
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                    filenames = [f for f in filenames if not f.startswith('.')]
                
                for dirname in dirs:
                    dir_path = os.path.join(root, dirname)
                    dir_info = self._get_file_info(dir_path)
                    files.append(dir_info)
                    dir_count += 1
                
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    file_info = self._get_file_info(file_path)
                    files.append(file_info)
                    total_size += file_info.get("size", 0)
                    file_count += 1
        else:
            for item in os.listdir(path):
                if not show_hidden and item.startswith('.'):
                    continue
                
                item_path = os.path.join(path, item)
                item_info = self._get_file_info(item_path)
                files.append(item_info)
                
                if os.path.isfile(item_path):
                    total_size += item_info.get("size", 0)
                    file_count += 1
                else:
                    dir_count += 1
        
        # 按类型和名称排序
        files.sort(key=lambda x: (x["type"] != "directory", x["name"].lower()))
        
        return SkillResult(
            success=True,
            message=f"列出 {path} 中的 {len(files)} 个项目",
            data={
                "path": path,
                "files": files,
                "total_files": file_count,
                "total_dirs": dir_count,
                "total_size": total_size,
                "recursive": recursive,
                "show_hidden": show_hidden
            }
        )
    
    async def _file_info(self, params: Dict[str, Any]) -> SkillResult:
        """获取文件信息"""
        path = params.get("path", "")
        
        if not os.path.exists(path):
            return SkillResult(
                success=False,
                message=f"文件不存在: {path}",
                error="File not found"
            )
        
        file_info = self._get_file_info(path, detailed=True)
        
        return SkillResult(
            success=True,
            message=f"文件信息: {path}",
            data=file_info
        )
    
    async def _copy_file(self, params: Dict[str, Any]) -> SkillResult:
        """复制文件或目录"""
        source = params.get("source", "")
        destination = params.get("destination", "")
        
        if not os.path.exists(source):
            return SkillResult(
                success=False,
                message=f"源文件不存在: {source}",
                error="Source not found"
            )
        
        try:
            if os.path.isdir(source):
                # 复制目录
                shutil.copytree(source, destination)
                operation = "copied directory"
            else:
                # 复制文件
                shutil.copy2(source, destination)
                operation = "copied file"
            
            return SkillResult(
                success=True,
                message=f"{operation}: {source} -> {destination}",
                data={
                    "source": source,
                    "destination": destination,
                    "operation": operation
                }
            )
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"复制失败: {str(e)}",
                error=str(e)
            )
    
    async def _move_file(self, params: Dict[str, Any]) -> SkillResult:
        """移动文件或目录"""
        source = params.get("source", "")
        destination = params.get("destination", "")
        
        if not os.path.exists(source):
            return SkillResult(
                success=False,
                message=f"源文件不存在: {source}",
                error="Source not found"
            )
        
        try:
            shutil.move(source, destination)
            
            operation = "moved directory" if os.path.isdir(source) else "moved file"
            
            return SkillResult(
                success=True,
                message=f"{operation}: {source} -> {destination}",
                data={
                    "source": source,
                    "destination": destination,
                    "operation": operation
                }
            )
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"移动失败: {str(e)}",
                error=str(e)
            )
    
    async def _delete_file(self, params: Dict[str, Any]) -> SkillResult:
        """删除文件或目录"""
        path = params.get("path", "")
        
        if not os.path.exists(path):
            return SkillResult(
                success=False,
                message=f"文件不存在: {path}",
                error="File not found"
            )
        
        try:
            if os.path.isdir(path):
                # 删除目录
                shutil.rmtree(path)
                operation = "deleted directory"
            else:
                # 删除文件
                os.remove(path)
                operation = "deleted file"
            
            return SkillResult(
                success=True,
                message=f"{operation}: {path}",
                data={
                    "path": path,
                    "operation": operation
                }
            )
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"删除失败: {str(e)}",
                error=str(e)
            )
    
    async def _search_files(self, params: Dict[str, Any]) -> SkillResult:
        """搜索文件"""
        path = params.get("path", ".")
        pattern = params.get("pattern", "*")
        max_results = params.get("max_results", 100)
        
        if not os.path.exists(path):
            return SkillResult(
                success=False,
                message=f"路径不存在: {path}",
                error="Path not found"
            )
        
        if not os.path.isdir(path):
            return SkillResult(
                success=False,
                message=f"不是目录: {path}",
                error="Not a directory"
            )
        
        import fnmatch
        results = []
        
        for root, dirs, files in os.walk(path):
            # 搜索文件
            for filename in fnmatch.filter(files, pattern):
                file_path = os.path.join(root, filename)
                file_info = self._get_file_info(file_path)
                results.append(file_info)
                
                if len(results) >= max_results:
                    break
            
            if len(results) >= max_results:
                break
        
        return SkillResult(
            success=True,
            message=f"搜索到 {len(results)} 个匹配文件",
            data={
                "path": path,
                "pattern": pattern,
                "results": results,
                "total_found": len(results)
            }
        )
    
    async def _file_hash(self, params: Dict[str, Any]) -> SkillResult:
        """计算文件哈希值"""
        path = params.get("path", "")
        algorithm = params.get("algorithm", "md5").lower()
        
        if not os.path.exists(path):
            return SkillResult(
                success=False,
                message=f"文件不存在: {path}",
                error="File not found"
            )
        
        if os.path.isdir(path):
            return SkillResult(
                success=False,
                message=f"不能计算目录哈希: {path}",
                error="Cannot hash directory"
            )
        
        # 支持的哈希算法
        supported_algorithms = ["md5", "sha1", "sha256", "sha512"]
        if algorithm not in supported_algorithms:
            return SkillResult(
                success=False,
                message=f"不支持的哈希算法: {algorithm}",
                error=f"Unsupported algorithm. Supported: {supported_algorithms}"
            )
        
        try:
            hash_func = hashlib.new(algorithm)
            
            async with aiofiles.open(path, 'rb') as f:
                while chunk := await f.read(8192):
                    hash_func.update(chunk)
            
            file_hash = hash_func.hexdigest()
            
            return SkillResult(
                success=True,
                message=f"{algorithm.upper()} 哈希值: {path}",
                data={
                    "path": path,
                    "algorithm": algorithm,
                    "hash": file_hash,
                    "size": os.path.getsize(path)
                }
            )
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"计算哈希失败: {str(e)}",
                error=str(e)
            )
    
    async def _file_size(self, params: Dict[str, Any]) -> SkillResult:
        """计算文件或目录大小"""
        path = params.get("path", ".")
        
        if not os.path.exists(path):
            return SkillResult(
                success=False,
                message=f"路径不存在: {path}",
                error="Path not found"
            )
        
        try:
            if os.path.isfile(path):
                size = os.path.getsize(path)
                file_count = 1
                dir_count = 0
            else:
                total_size = 0
                file_count = 0
                dir_count = 0
                
                for root, dirs, files in os.walk(path):
                    dir_count += len(dirs)
                    for filename in files:
                        file_path = os.path.join(root, filename)
                        if os.path.isfile(file_path):
                            total_size += os.path.getsize(file_path)
                            file_count += 1
                
                size = total_size
            
            # 格式化大小
            size_str = self._format_size(size)
            
            return SkillResult(
                success=True,
                message=f"大小: {path}",
                data={
                    "path": path,
                    "size_bytes": size,
                    "size_formatted": size_str,
                    "file_count": file_count,
                    "dir_count": dir_count,
                    "is_file": os.path.isfile(path),
                    "is_dir": os.path.isdir(path)
                }
            )
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"计算大小失败: {str(e)}",
                error=str(e)
            )
    
    def _get_file_info(self, path: str, detailed: bool = False) -> Dict[str, Any]:
        """获取文件信息"""
        stat = os.stat(path)
        
        info = {
            "name": os.path.basename(path),
            "path": path,
            "type": "file" if os.path.isfile(path) else "directory",
            "size": stat.st_size if os.path.isfile(path) else 0,
            "size_formatted": self._format_size(stat.st_size) if os.path.isfile(path) else "-",
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "permissions": oct(stat.st_mode)[-3:],
            "owner": stat.st_uid,
            "group": stat.st_gid
        }
        
        if detailed and os.path.isfile(path):
            # 获取MIME类型
            mime_type, encoding = mimetypes.guess_type(path)
            info["mime_type"] = mime_type or "unknown"
            info["encoding"] = encoding or "unknown"
            
            # 获取文件扩展名
            info["extension"] = pathlib.Path(path).suffix.lower()
            
            # 如果是文本文件，尝试读取前几行
            if mime_type and mime_type.startswith('text/'):
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        preview_lines = []
                        for _ in range(5):
                            line = f.readline()
                            if not line:
                                break
                            preview_lines.append(line.strip())
                        info["preview"] = "\n".join(preview_lines)
                except:
                    info["preview"] = "无法预览"
        
        return info
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"
        
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        
        size = float(size_bytes)
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.2f} {units[unit_index]}"