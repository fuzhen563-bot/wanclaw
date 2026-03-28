"""
日志查看技能
提供日志文件查看和分析功能
"""

import os
import re
import gzip
import bz2
import logging
import tempfile
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter

from wanclaw.backend.skills import BaseSkill, SkillResult, SkillCategory, SkillLevel
from wanclaw.backend.im_adapter.security import get_security, OperationType


logger = logging.getLogger(__name__)


class LogViewerSkill(BaseSkill):
    """日志查看技能"""
    
    def __init__(self):
        super().__init__()
        self.name = "LogViewer"
        self.description = "日志查看：查看、搜索、分析日志文件"
        self.category = SkillCategory.OPS
        self.level = SkillLevel.INTERMEDIATE
        
        # 必需参数
        self.required_params = ["action"]
        
        # 可选参数及其类型
        self.optional_params = {
            "log_path": str,
            "log_directory": str,
            "search_pattern": str,
            "filter_level": str,
            "start_time": str,
            "end_time": str,
            "lines": int,
            "tail": bool,
            "follow": bool,
            "max_files": int,
            "analyze_patterns": bool,
            "extract_errors": bool,
            "format": str
        }
    
    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        """
        执行日志查看操作
        
        Args:
            params: {
                "action": "view|search|tail|list|analyze|errors|stats|rotate",
                "log_path": "/var/log/syslog",
                "log_directory": "/var/log",
                "search_pattern": "ERROR|error",
                "filter_level": "ERROR|WARN|INFO|DEBUG",
                "start_time": "2024-01-01T00:00:00",
                "end_time": "2024-01-02T00:00:00",
                "lines": 100,
                "tail": true,
                "follow": false,
                "max_files": 10,
                "analyze_patterns": true,
                "extract_errors": true,
                "format": "text|json|csv"
            }
            
        Returns:
            执行结果
        """
        action = params.get("action", "").lower()
        user_id = params.get("user_id", "unknown")
        username = params.get("username", "unknown")
        
        # 安全检查（读取操作）
        security = get_security()
        
        if action in ["view", "search", "tail", "analyze", "errors", "stats"]:
            log_path = params.get("log_path", "")
            if log_path:
                allowed, reason = security.check_file_access(
                    log_path, OperationType.FILE_READ, user_id, username
                )
                if not allowed:
                    return SkillResult(
                        success=False,
                        message=f"日志访问被拒绝: {reason}",
                        error="Security check failed"
                    )
        
        elif action == "list":
            log_directory = params.get("log_directory", "/var/log")
            allowed, reason = security.check_file_access(
                log_directory, OperationType.FILE_READ, user_id, username
            )
            if not allowed:
                return SkillResult(
                    success=False,
                    message=f"目录访问被拒绝: {reason}",
                    error="Security check failed"
                )
        
        try:
            if action == "view":
                return await self._view_log(params)
            elif action == "search":
                return await self._search_log(params)
            elif action == "tail":
                return await self._tail_log(params)
            elif action == "list":
                return await self._list_logs(params)
            elif action == "analyze":
                return await self._analyze_log(params)
            elif action == "errors":
                return await self._extract_errors(params)
            elif action == "stats":
                return await self._log_stats(params)
            elif action == "rotate":
                return await self._rotate_log(params)
            else:
                return SkillResult(
                    success=False,
                    message=f"不支持的操作: {action}",
                    error=f"Unsupported action: {action}"
                )
        except Exception as e:
            logger.error(f"日志操作失败: {action} - {e}")
            return SkillResult(
                success=False,
                message=f"日志操作失败: {str(e)}",
                error=str(e)
            )
    
    async def _view_log(self, params: Dict[str, Any]) -> SkillResult:
        """查看日志文件"""
        log_path = params.get("log_path", "")
        lines = params.get("lines", 100)
        tail = params.get("tail", False)
        follow = params.get("follow", False)
        filter_level = params.get("filter_level", "")
        
        if not log_path:
            return SkillResult(
                success=False,
                message="需要日志文件路径",
                error="Log path required"
            )
        
        if not os.path.exists(log_path):
            return SkillResult(
                success=False,
                message=f"日志文件不存在: {log_path}",
                error="Log file not found"
            )
        
        try:
            # 读取日志文件
            log_lines = self._read_log_file(log_path, lines, tail)
            
            # 过滤日志级别
            if filter_level:
                log_lines = [line for line in log_lines if self._contains_log_level(line, filter_level)]
            
            # 添加行号
            log_lines_with_numbers = []
            for i, line in enumerate(log_lines, 1):
                log_lines_with_numbers.append({
                    "line_number": i,
                    "content": line,
                    "timestamp": self._extract_timestamp(line),
                    "level": self._extract_log_level(line)
                })
            
            # 获取文件信息
            file_info = self._get_file_info(log_path)
            
            return SkillResult(
                success=True,
                message=f"查看日志: {log_path}",
                data={
                    "log_path": log_path,
                    "lines": len(log_lines_with_numbers),
                    "total_lines": lines,
                    "tail": tail,
                    "follow": follow,
                    "filter_level": filter_level or "无",
                    "log_lines": log_lines_with_numbers,
                    "file_info": file_info
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"查看日志失败: {str(e)}",
                error=str(e)
            )
    
    async def _search_log(self, params: Dict[str, Any]) -> SkillResult:
        """搜索日志文件"""
        log_path = params.get("log_path", "")
        search_pattern = params.get("search_pattern", "")
        lines = params.get("lines", 1000)
        case_sensitive = params.get("case_sensitive", False)
        
        if not log_path:
            return SkillResult(
                success=False,
                message="需要日志文件路径",
                error="Log path required"
            )
        
        if not search_pattern:
            return SkillResult(
                success=False,
                message="需要搜索模式",
                error="Search pattern required"
            )
        
        if not os.path.exists(log_path):
            return SkillResult(
                success=False,
                message=f"日志文件不存在: {log_path}",
                error="Log file not found"
            )
        
        try:
            # 读取日志文件
            log_lines = self._read_log_file(log_path, lines, False)
            
            # 编译正则表达式
            try:
                if case_sensitive:
                    pattern = re.compile(search_pattern)
                else:
                    pattern = re.compile(search_pattern, re.IGNORECASE)
            except re.error:
                # 如果正则表达式无效，使用字符串搜索
                pattern = None
            
            # 搜索匹配行
            matches = []
            for i, line in enumerate(log_lines, 1):
                if pattern:
                    if pattern.search(line):
                        matches.append({
                            "line_number": i,
                            "content": line,
                            "timestamp": self._extract_timestamp(line),
                            "level": self._extract_log_level(line)
                        })
                else:
                    if (case_sensitive and search_pattern in line) or \
                       (not case_sensitive and search_pattern.lower() in line.lower()):
                        matches.append({
                            "line_number": i,
                            "content": line,
                            "timestamp": self._extract_timestamp(line),
                            "level": self._extract_log_level(line)
                        })
            
            # 获取文件信息
            file_info = self._get_file_info(log_path)
            
            return SkillResult(
                success=True,
                message=f"搜索到 {len(matches)} 个匹配项",
                data={
                    "log_path": log_path,
                    "search_pattern": search_pattern,
                    "case_sensitive": case_sensitive,
                    "matches": matches,
                    "total_matches": len(matches),
                    "lines_searched": len(log_lines),
                    "file_info": file_info
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"搜索日志失败: {str(e)}",
                error=str(e)
            )
    
    async def _tail_log(self, params: Dict[str, Any]) -> SkillResult:
        """实时查看日志"""
        log_path = params.get("log_path", "")
        lines = params.get("lines", 50)
        follow = params.get("follow", False)
        
        if not log_path:
            return SkillResult(
                success=False,
                message="需要日志文件路径",
                error="Log path required"
            )
        
        if not os.path.exists(log_path):
            return SkillResult(
                success=False,
                message=f"日志文件不存在: {log_path}",
                error="Log file not found"
            )
        
        try:
            # 读取最后几行
            log_lines = self._read_log_file(log_path, lines, True)
            
            # 添加行号
            log_lines_with_numbers = []
            for i, line in enumerate(log_lines, 1):
                log_lines_with_numbers.append({
                    "line_number": i,
                    "content": line,
                    "timestamp": self._extract_timestamp(line),
                    "level": self._extract_log_level(line)
                })
            
            # 获取文件信息
            file_info = self._get_file_info(log_path)
            
            return SkillResult(
                success=True,
                message=f"实时查看日志: {log_path}",
                data={
                    "log_path": log_path,
                    "lines": len(log_lines_with_numbers),
                    "follow": follow,
                    "log_lines": log_lines_with_numbers,
                    "file_info": file_info,
                    "last_modified": file_info.get("modified"),
                    "follow_enabled": follow
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"实时查看日志失败: {str(e)}",
                error=str(e)
            )
    
    async def _list_logs(self, params: Dict[str, Any]) -> SkillResult:
        """列出日志文件"""
        log_directory = params.get("log_directory", "/var/log")
        max_files = params.get("max_files", 50)
        
        if not os.path.exists(log_directory):
            return SkillResult(
                success=False,
                message=f"目录不存在: {log_directory}",
                error="Directory not found"
            )
        
        if not os.path.isdir(log_directory):
            return SkillResult(
                success=False,
                message=f"不是目录: {log_directory}",
                error="Not a directory"
            )
        
        try:
            # 查找日志文件
            log_files = []
            total_size = 0
            
            for root, dirs, files in os.walk(log_directory):
                # 跳过某些目录
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for filename in files:
                    file_path = os.path.join(root, filename)
                    
                    # 检查是否为日志文件
                    if self._is_log_file(filename):
                        try:
                            stat = os.stat(file_path)
                            file_info = {
                                "name": filename,
                                "path": file_path,
                                "size": stat.st_size,
                                "size_formatted": self._format_size(stat.st_size),
                                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                                "type": self._get_log_file_type(filename)
                            }
                            
                            log_files.append(file_info)
                            total_size += stat.st_size
                            
                            # 限制文件数量
                            if len(log_files) >= max_files:
                                break
                                
                        except (OSError, PermissionError):
                            continue
                
                if len(log_files) >= max_files:
                    break
            
            # 按修改时间排序
            log_files.sort(key=lambda x: x["modified"], reverse=True)
            
            # 按类型统计
            type_stats = {}
            for log_file in log_files:
                file_type = log_file["type"]
                type_stats[file_type] = type_stats.get(file_type, 0) + 1
            
            return SkillResult(
                success=True,
                message=f"找到 {len(log_files)} 个日志文件",
                data={
                    "directory": log_directory,
                    "log_files": log_files,
                    "total_files": len(log_files),
                    "total_size": total_size,
                    "total_size_formatted": self._format_size(total_size),
                    "type_stats": type_stats,
                    "max_files": max_files
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"列出日志文件失败: {str(e)}",
                error=str(e)
            )
    
    async def _analyze_log(self, params: Dict[str, Any]) -> SkillResult:
        """分析日志文件"""
        log_path = params.get("log_path", "")
        lines = params.get("lines", 5000)
        analyze_patterns = params.get("analyze_patterns", True)
        
        if not log_path:
            return SkillResult(
                success=False,
                message="需要日志文件路径",
                error="Log path required"
            )
        
        if not os.path.exists(log_path):
            return SkillResult(
                success=False,
                message=f"日志文件不存在: {log_path}",
                error="Log file not found"
            )
        
        try:
            # 读取日志文件
            log_lines = self._read_log_file(log_path, lines, False)
            
            # 分析日志
            analysis = {
                "total_lines": len(log_lines),
                "level_stats": {},
                "hourly_stats": defaultdict(int),
                "daily_stats": defaultdict(int),
                "common_patterns": [],
                "error_patterns": [],
                "warning_patterns": [],
                "top_messages": []
            }
            
            # 统计日志级别
            level_counter = Counter()
            message_counter = Counter()
            
            for line in log_lines:
                # 提取日志级别
                level = self._extract_log_level(line)
                level_counter[level] += 1
                
                # 提取时间戳
                timestamp = self._extract_timestamp(line)
                if timestamp:
                    # 按小时统计
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        hour_key = dt.strftime("%Y-%m-%d %H:00")
                        analysis["hourly_stats"][hour_key] += 1
                        
                        day_key = dt.strftime("%Y-%m-%d")
                        analysis["daily_stats"][day_key] += 1
                    except:
                        pass
                
                # 统计常见消息
                if analyze_patterns:
                    # 提取消息内容（去除时间戳和级别）
                    message = self._extract_log_message(line)
                    if message:
                        message_counter[message[:100]] += 1
            
            # 更新级别统计
            for level, count in level_counter.items():
                analysis["level_stats"][level] = {
                    "count": count,
                    "percentage": (count / len(log_lines)) * 100
                }
            
            # 获取最常见消息
            for message, count in message_counter.most_common(10):
                analysis["top_messages"].append({
                    "message": message,
                    "count": count,
                    "percentage": (count / len(log_lines)) * 100
                })
            
            # 识别错误和警告模式
            error_keywords = ["error", "exception", "failed", "failure", "crash", "panic"]
            warning_keywords = ["warning", "warn", "deprecated", "obsolete"]
            
            for line in log_lines:
                line_lower = line.lower()
                
                # 检查错误关键词
                for keyword in error_keywords:
                    if keyword in line_lower:
                        analysis["error_patterns"].append({
                            "keyword": keyword,
                            "line": line[:200]
                        })
                        break
                
                # 检查警告关键词
                for keyword in warning_keywords:
                    if keyword in line_lower:
                        analysis["warning_patterns"].append({
                            "keyword": keyword,
                            "line": line[:200]
                        })
                        break
            
            # 去重错误和警告模式
            analysis["error_patterns"] = list({item["line"]: item for item in analysis["error_patterns"]}.values())[:20]
            analysis["warning_patterns"] = list({item["line"]: item for item in analysis["warning_patterns"]}.values())[:20]
            
            # 获取文件信息
            file_info = self._get_file_info(log_path)
            
            return SkillResult(
                success=True,
                message=f"日志分析完成: {log_path}",
                data={
                    "log_path": log_path,
                    "analysis": analysis,
                    "lines_analyzed": len(log_lines),
                    "file_info": file_info
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"分析日志失败: {str(e)}",
                error=str(e)
            )
    
    async def _extract_errors(self, params: Dict[str, Any]) -> SkillResult:
        """提取错误日志"""
        log_path = params.get("log_path", "")
        lines = params.get("lines", 1000)
        
        if not log_path:
            return SkillResult(
                success=False,
                message="需要日志文件路径",
                error="Log path required"
            )
        
        if not os.path.exists(log_path):
            return SkillResult(
                success=False,
                message=f"日志文件不存在: {log_path}",
                error="Log file not found"
            )
        
        try:
            # 读取日志文件
            log_lines = self._read_log_file(log_path, lines, False)
            
            # 提取错误行
            errors = []
            error_keywords = ["error", "exception", "failed", "failure", "crash", "panic", "segmentation fault"]
            
            for i, line in enumerate(log_lines, 1):
                line_lower = line.lower()
                
                # 检查是否包含错误关键词
                is_error = False
                matched_keyword = ""
                
                for keyword in error_keywords:
                    if keyword in line_lower:
                        is_error = True
                        matched_keyword = keyword
                        break
                
                # 检查日志级别
                level = self._extract_log_level(line)
                if level and level.upper() in ["ERROR", "FATAL", "CRITICAL"]:
                    is_error = True
                    matched_keyword = level
                
                if is_error:
                    errors.append({
                        "line_number": i,
                        "content": line,
                        "timestamp": self._extract_timestamp(line),
                        "level": level or "UNKNOWN",
                        "matched_keyword": matched_keyword
                    })
            
            # 按错误类型分组
            error_groups = defaultdict(list)
            for error in errors:
                error_groups[error["matched_keyword"]].append(error)
            
            # 统计
            error_stats = {}
            for keyword, error_list in error_groups.items():
                error_stats[keyword] = len(error_list)
            
            # 获取文件信息
            file_info = self._get_file_info(log_path)
            
            return SkillResult(
                success=True,
                message=f"提取到 {len(errors)} 个错误",
                data={
                    "log_path": log_path,
                    "errors": errors,
                    "total_errors": len(errors),
                    "error_groups": dict(error_groups),
                    "error_stats": error_stats,
                    "lines_searched": len(log_lines),
                    "file_info": file_info
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"提取错误日志失败: {str(e)}",
                error=str(e)
            )
    
    async def _log_stats(self, params: Dict[str, Any]) -> SkillResult:
        """日志统计信息"""
        log_directory = params.get("log_directory", "/var/log")
        
        if not os.path.exists(log_directory):
            return SkillResult(
                success=False,
                message=f"目录不存在: {log_directory}",
                error="Directory not found"
            )
        
        try:
            # 收集统计信息
            stats = {
                "total_logs": 0,
                "total_size": 0,
                "largest_log": None,
                "oldest_log": None,
                "newest_log": None,
                "by_type": defaultdict(lambda: {"count": 0, "size": 0}),
                "by_extension": defaultdict(lambda: {"count": 0, "size": 0}),
                "recent_logs": []
            }
            
            # 遍历日志目录
            for root, dirs, files in os.walk(log_directory):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for filename in files:
                    file_path = os.path.join(root, filename)
                    
                    # 检查是否为日志文件
                    if self._is_log_file(filename):
                        try:
                            stat = os.stat(file_path)
                            file_size = stat.st_size
                            modified_time = stat.st_mtime
                            
                            # 更新统计
                            stats["total_logs"] += 1
                            stats["total_size"] += file_size
                            
                            # 按类型统计
                            file_type = self._get_log_file_type(filename)
                            stats["by_type"][file_type]["count"] += 1
                            stats["by_type"][file_type]["size"] += file_size
                            
                            # 按扩展名统计
                            _, ext = os.path.splitext(filename)
                            ext = ext.lower()
                            stats["by_extension"][ext]["count"] += 1
                            stats["by_extension"][ext]["size"] += file_size
                            
                            # 更新最大/最小/最新文件
                            file_info = {
                                "path": file_path,
                                "name": filename,
                                "size": file_size,
                                "size_formatted": self._format_size(file_size),
                                "modified": datetime.fromtimestamp(modified_time).isoformat(),
                                "type": file_type
                            }
                            
                            # 最大文件
                            if (stats["largest_log"] is None or 
                                file_size > stats["largest_log"]["size"]):
                                stats["largest_log"] = file_info
                            
                            # 最新文件
                            if (stats["newest_log"] is None or 
                                modified_time > stats["newest_log"]["modified_timestamp"]):
                                stats["newest_log"] = file_info
                                stats["newest_log"]["modified_timestamp"] = modified_time
                            
                            # 最旧文件
                            if (stats["oldest_log"] is None or 
                                modified_time < stats["oldest_log"]["modified_timestamp"]):
                                stats["oldest_log"] = file_info
                                stats["oldest_log"]["modified_timestamp"] = modified_time
                            
                            # 最近修改的文件（24小时内）
                            if datetime.now().timestamp() - modified_time < 86400:
                                stats["recent_logs"].append(file_info)
                                
                        except (OSError, PermissionError):
                            continue
            
            # 限制最近日志数量
            stats["recent_logs"].sort(key=lambda x: x.get("modified_timestamp", 0), reverse=True)
            stats["recent_logs"] = stats["recent_logs"][:10]
            
            # 删除时间戳字段
            if stats["newest_log"]:
                stats["newest_log"].pop("modified_timestamp", None)
            if stats["oldest_log"]:
                stats["oldest_log"].pop("modified_timestamp", None)
            
            # 格式化大小
            stats["total_size_formatted"] = self._format_size(stats["total_size"])
            
            # 计算平均大小
            if stats["total_logs"] > 0:
                stats["average_size"] = stats["total_size"] / stats["total_logs"]
                stats["average_size_formatted"] = self._format_size(stats["average_size"])
            else:
                stats["average_size"] = 0
                stats["average_size_formatted"] = "0 B"
            
            return SkillResult(
                success=True,
                message=f"日志统计信息: {log_directory}",
                data=stats
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"获取日志统计失败: {str(e)}",
                error=str(e)
            )
    
    async def _rotate_log(self, params: Dict[str, Any]) -> SkillResult:
        """轮转日志文件（模拟）"""
        log_path = params.get("log_path", "")
        
        if not log_path:
            return SkillResult(
                success=False,
                message="需要日志文件路径",
                error="Log path required"
            )
        
        if not os.path.exists(log_path):
            return SkillResult(
                success=False,
                message=f"日志文件不存在: {log_path}",
                error="Log file not found"
            )
        
        try:
            # 获取原始文件信息
            stat = os.stat(log_path)
            original_size = stat.st_size
            
            # 模拟轮转：创建备份并清空文件
            import shutil
            import time
            
            # 创建备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{log_path}.{timestamp}.bak"
            
            # 复制文件到备份
            shutil.copy2(log_path, backup_path)
            
            # 清空原始文件
            with open(log_path, 'w') as f:
                f.write(f"# Log rotated at {datetime.now().isoformat()}\n")
                f.write(f"# Original size: {original_size} bytes\n")
                f.write(f"# Backup: {backup_path}\n")
            
            # 获取新文件信息
            new_stat = os.stat(log_path)
            new_size = new_stat.st_size
            
            return SkillResult(
                success=True,
                message=f"日志轮转完成: {log_path}",
                data={
                    "log_path": log_path,
                    "backup_path": backup_path,
                    "original_size": original_size,
                    "original_size_formatted": self._format_size(original_size),
                    "new_size": new_size,
                    "new_size_formatted": self._format_size(new_size),
                    "reduction": original_size - new_size,
                    "reduction_formatted": self._format_size(original_size - new_size),
                    "rotation_time": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"日志轮转失败: {str(e)}",
                error=str(e)
            )
    
    # ===== 辅助方法 =====
    
    def _read_log_file(self, file_path: str, lines: int = 100, tail: bool = False) -> List[str]:
        """读取日志文件"""
        # 检查文件类型
        if file_path.endswith('.gz'):
            return self._read_gzip_file(file_path, lines, tail)
        elif file_path.endswith('.bz2'):
            return self._read_bz2_file(file_path, lines, tail)
        else:
            return self._read_text_file(file_path, lines, tail)
    
    def _read_text_file(self, file_path: str, lines: int, tail: bool) -> List[str]:
        """读取文本文件"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            if tail:
                # 读取最后N行
                total_lines = []
                buffer_size = 8192
                file_size = os.path.getsize(file_path)
                
                # 从文件末尾开始读取
                with open(file_path, 'rb') as f_binary:
                    f_binary.seek(0, 2)  # 移动到文件末尾
                    position = f_binary.tell()
                    buffer = bytearray()
                    
                    while position > 0 and len(total_lines) < lines:
                        # 计算读取位置
                        read_size = min(buffer_size, position)
                        position -= read_size
                        f_binary.seek(position)
                        
                        # 读取数据
                        chunk = f_binary.read(read_size)
                        buffer.extend(chunk)
                        
                        # 处理缓冲区
                        while b'\n' in buffer:
                            line_end = buffer.rfind(b'\n')
                            if line_end == len(buffer) - 1:
                                buffer.pop()
                                continue
                            
                            line = buffer[line_end+1:].decode('utf-8', errors='ignore')
                            total_lines.append(line.rstrip('\n'))
                            buffer = buffer[:line_end]
                    
                    # 处理剩余缓冲区
                    if buffer:
                        line = buffer.decode('utf-8', errors='ignore')
                        total_lines.append(line.rstrip('\n'))
                
                # 反转行顺序
                total_lines.reverse()
                return total_lines
            else:
                # 读取前N行
                total_lines = []
                for i, line in enumerate(f):
                    if i >= lines:
                        break
                    total_lines.append(line.rstrip('\n'))
                return total_lines
    
    def _read_gzip_file(self, file_path: str, lines: int, tail: bool) -> List[str]:
        """读取gzip压缩文件"""
        import gzip
        
        with gzip.open(file_path, 'rt', encoding='utf-8', errors='ignore') as f:
            if tail:
                # 对于压缩文件，简单读取所有行然后取最后N行
                all_lines = f.readlines()
                return [line.rstrip('\n') for line in all_lines[-lines:]]
            else:
                total_lines = []
                for i, line in enumerate(f):
                    if i >= lines:
                        break
                    total_lines.append(line.rstrip('\n'))
                return total_lines
    
    def _read_bz2_file(self, file_path: str, lines: int, tail: bool) -> List[str]:
        """读取bz2压缩文件"""
        import bz2
        
        with bz2.open(file_path, 'rt', encoding='utf-8', errors='ignore') as f:
            if tail:
                # 对于压缩文件，简单读取所有行然后取最后N行
                all_lines = f.readlines()
                return [line.rstrip('\n') for line in all_lines[-lines:]]
            else:
                total_lines = []
                for i, line in enumerate(f):
                    if i >= lines:
                        break
                    total_lines.append(line.rstrip('\n'))
                return total_lines
    
    def _extract_timestamp(self, line: str) -> Optional[str]:
        """从日志行提取时间戳"""
        # 常见时间戳格式
        timestamp_patterns = [
            r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)',  # ISO格式
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?)',  # 空格分隔
            r'(\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})',  # 日期分隔符
            r'(\w{3} \d{2} \d{2}:\d{2}:\d{2})',  # Syslog格式
            r'(\d{10,13})',  # 时间戳（秒或毫秒）
        ]
        
        for pattern in timestamp_patterns:
            match = re.search(pattern, line)
            if match:
                timestamp = match.group(1)
                
                # 如果是Unix时间戳，转换为ISO格式
                if re.match(r'^\d{10,13}$', timestamp):
                    try:
                        ts = int(timestamp)
                        if ts > 9999999999:  # 毫秒
                            ts = ts / 1000
                        return datetime.fromtimestamp(ts).isoformat()
                    except:
                        return timestamp
                
                return timestamp
        
        return None
    
    def _extract_log_level(self, line: str) -> Optional[str]:
        """从日志行提取日志级别"""
        level_patterns = [
            r'\b(ERROR|ERR|FATAL|CRITICAL)\b',
            r'\b(WARNING|WARN)\b',
            r'\b(INFO)\b',
            r'\b(DEBUG)\b',
            r'\b(TRACE)\b'
        ]
        
        for pattern in level_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        return None
    
    def _extract_log_message(self, line: str) -> str:
        """从日志行提取消息内容"""
        # 尝试移除时间戳和级别
        patterns_to_remove = [
            r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\s*',
            r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d+)?\s*',
            r'^\w{3} \d{2} \d{2}:\d{2}:\d{2}\s*',
            r'\b(ERROR|ERR|FATAL|CRITICAL|WARNING|WARN|INFO|DEBUG|TRACE)\b\s*'
        ]
        
        message = line
        for pattern in patterns_to_remove:
            message = re.sub(pattern, '', message, flags=re.IGNORECASE)
        
        return message.strip()
    
    def _contains_log_level(self, line: str, level_filter: str) -> bool:
        """检查日志行是否包含指定级别"""
        level = self._extract_log_level(line)
        if not level:
            return False
        
        level_map = {
            "ERROR": ["ERROR", "ERR", "FATAL", "CRITICAL"],
            "WARN": ["WARNING", "WARN"],
            "INFO": ["INFO"],
            "DEBUG": ["DEBUG", "TRACE"]
        }
        
        filter_upper = level_filter.upper()
        if filter_upper in level_map:
            return level in level_map[filter_upper]
        
        return level == filter_upper
    
    def _is_log_file(self, filename: str) -> bool:
        """检查是否为日志文件"""
        log_extensions = ['.log', '.txt', '.out', '.err']
        log_patterns = [
            r'.*\.log(\.\d+)?$',
            r'.*\.log\.gz$',
            r'.*\.log\.bz2$',
            r'.*\.txt$',
            r'.*\.out$',
            r'.*\.err$',
            r'^messages$',
            r'^syslog$',
            r'^auth\.log$',
            r'^daemon\.log$',
            r'^kern\.log$'
        ]
        
        filename_lower = filename.lower()
        
        # 检查扩展名
        for ext in log_extensions:
            if filename_lower.endswith(ext):
                return True
        
        # 检查模式
        for pattern in log_patterns:
            if re.match(pattern, filename_lower):
                return True
        
        return False
    
    def _get_log_file_type(self, filename: str) -> str:
        """获取日志文件类型"""
        filename_lower = filename.lower()
        
        if filename_lower.endswith('.gz'):
            return "gzip"
        elif filename_lower.endswith('.bz2'):
            return "bzip2"
        elif filename_lower.endswith('.log'):
            return "log"
        elif filename_lower.endswith('.txt'):
            return "text"
        elif filename_lower.endswith('.out'):
            return "output"
        elif filename_lower.endswith('.err'):
            return "error"
        elif 'access' in filename_lower:
            return "access"
        elif 'error' in filename_lower:
            return "error"
        elif 'debug' in filename_lower:
            return "debug"
        else:
            return "general"
    
    def _get_file_info(self, file_path: str) -> Dict[str, Any]:
        """获取文件信息"""
        stat = os.stat(file_path)
        
        return {
            "path": file_path,
            "name": os.path.basename(file_path),
            "size": stat.st_size,
            "size_formatted": self._format_size(stat.st_size),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "type": self._get_log_file_type(os.path.basename(file_path))
        }
    
    def _format_size(self, bytes_size: int) -> str:
        """格式化文件大小"""
        if bytes_size == 0:
            return "0 B"
        
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0
        
        size = float(bytes_size)
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        return f"{size:.2f} {units[unit_index]}"