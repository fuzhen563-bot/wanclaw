"""
进程监控技能
提供系统进程查看和管理功能
"""

import os
import sys
import psutil
import logging
import subprocess
import signal
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from wanclaw.backend.skills import BaseSkill, SkillResult, SkillCategory, SkillLevel


logger = logging.getLogger(__name__)


class ProcessMonitorSkill(BaseSkill):
    """进程监控技能"""
    
    def __init__(self):
        super().__init__()
        self.name = "ProcessMonitor"
        self.description = "进程监控：查看、管理、监控系统进程"
        self.category = SkillCategory.OPS
        self.level = SkillLevel.INTERMEDIATE
        
        # 必需参数
        self.required_params = ["action"]
        
        # 可选参数及其类型
        self.optional_params = {
            "pid": int,
            "process_name": str,
            "search_term": str,
            "signal": str,
            "sort_by": str,
            "reverse": bool,
            "limit": int,
            "user": str,
            "cpu_threshold": float,
            "memory_threshold": float,
            "duration": int
        }
    
    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        """
        执行进程监控操作
        
        Args:
            params: {
                "action": "list|info|search|kill|pause|resume|tree|stats|monitor",
                "pid": 1234,
                "process_name": "nginx",
                "search_term": "python",
                "signal": "SIGTERM|SIGKILL|SIGSTOP|SIGCONT",
                "sort_by": "cpu|memory|pid|name|user",
                "reverse": false,
                "limit": 20,
                "user": "root",
                "cpu_threshold": 80.0,
                "memory_threshold": 80.0,
                "duration": 60
            }
            
        Returns:
            执行结果
        """
        action = params.get("action", "").lower()
        
        try:
            if action == "list":
                return await self._list_processes(params)
            elif action == "info":
                return await self._process_info(params)
            elif action == "search":
                return await self._search_processes(params)
            elif action == "kill":
                return await self._kill_process(params)
            elif action == "pause":
                return await self._pause_process(params)
            elif action == "resume":
                return await self._resume_process(params)
            elif action == "tree":
                return await self._process_tree(params)
            elif action == "stats":
                return await self._process_stats(params)
            elif action == "monitor":
                return await self._monitor_processes(params)
            else:
                return SkillResult(
                    success=False,
                    message=f"不支持的操作: {action}",
                    error=f"Unsupported action: {action}"
                )
        except Exception as e:
            logger.error(f"进程监控操作失败: {action} - {e}")
            return SkillResult(
                success=False,
                message=f"进程监控操作失败: {str(e)}",
                error=str(e)
            )
    
    async def _list_processes(self, params: Dict[str, Any]) -> SkillResult:
        """列出系统进程"""
        sort_by = params.get("sort_by", "pid")
        reverse = params.get("reverse", False)
        limit = params.get("limit", 50)
        user_filter = params.get("user", "")
        
        try:
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 
                                            'memory_percent', 'status', 'create_time']):
                try:
                    proc_info = proc.info
                    
                    # 用户过滤
                    if user_filter and proc_info.get('username') != user_filter:
                        continue
                    
                    # 计算运行时间
                    create_time = proc_info.get('create_time')
                    if create_time:
                        uptime = datetime.now().timestamp() - create_time
                        uptime_str = self._format_duration(uptime)
                    else:
                        uptime_str = "未知"
                    
                    processes.append({
                        "pid": proc_info.get('pid'),
                        "name": proc_info.get('name'),
                        "user": proc_info.get('username'),
                        "cpu_percent": proc_info.get('cpu_percent', 0.0),
                        "memory_percent": proc_info.get('memory_percent', 0.0),
                        "status": proc_info.get('status'),
                        "uptime": uptime_str,
                        "create_time": datetime.fromtimestamp(create_time).isoformat() if create_time else "未知"
                    })
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # 排序
            if sort_by == "cpu":
                processes.sort(key=lambda x: x.get("cpu_percent", 0), reverse=not reverse)
            elif sort_by == "memory":
                processes.sort(key=lambda x: x.get("memory_percent", 0), reverse=not reverse)
            elif sort_by == "pid":
                processes.sort(key=lambda x: x.get("pid", 0), reverse=reverse)
            elif sort_by == "name":
                processes.sort(key=lambda x: x.get("name", "").lower(), reverse=reverse)
            elif sort_by == "user":
                processes.sort(key=lambda x: x.get("user", "").lower(), reverse=reverse)
            
            # 限制数量
            if limit > 0:
                processes = processes[:limit]
            
            # 系统统计
            total_processes = len(processes)
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory_usage = psutil.virtual_memory().percent
            
            return SkillResult(
                success=True,
                message=f"列出 {total_processes} 个进程",
                data={
                    "processes": processes,
                    "total": total_processes,
                    "system_cpu": cpu_usage,
                    "system_memory": memory_usage,
                    "sort_by": sort_by,
                    "reverse": reverse,
                    "user_filter": user_filter or "无"
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"列出进程失败: {str(e)}",
                error=str(e)
            )
    
    async def _process_info(self, params: Dict[str, Any]) -> SkillResult:
        """获取进程详细信息"""
        pid = params.get("pid")
        process_name = params.get("process_name", "")
        
        if not pid and not process_name:
            return SkillResult(
                success=False,
                message="需要PID或进程名称",
                error="PID or process name required"
            )
        
        try:
            if pid:
                proc = psutil.Process(pid)
            else:
                # 根据进程名称查找
                found = False
                for p in psutil.process_iter(['pid', 'name']):
                    if p.info.get('name') == process_name:
                        proc = psutil.Process(p.info.get('pid'))
                        found = True
                        break
                
                if not found:
                    return SkillResult(
                        success=False,
                        message=f"未找到进程: {process_name}",
                        error="Process not found"
                    )
            
            # 获取进程信息
            with proc.oneshot():
                # 基本信息
                proc_info = {
                    "pid": proc.pid,
                    "name": proc.name(),
                    "exe": proc.exe() if proc.exe() else "未知",
                    "cmdline": proc.cmdline(),
                    "cwd": proc.cwd() if proc.cwd() else "未知",
                    "username": proc.username(),
                    "status": proc.status(),
                    "create_time": datetime.fromtimestamp(proc.create_time()).isoformat(),
                    "uptime": self._format_duration(datetime.now().timestamp() - proc.create_time()),
                    "nice": proc.nice()
                }
                
                # CPU和内存信息
                cpu_times = proc.cpu_times()
                memory_info = proc.memory_info()
                memory_full_info = proc.memory_full_info() if hasattr(proc, 'memory_full_info') else None
                
                proc_info.update({
                    "cpu_percent": proc.cpu_percent(interval=0.1),
                    "cpu_times_user": cpu_times.user,
                    "cpu_times_system": cpu_times.system,
                    "memory_percent": proc.memory_percent(),
                    "memory_rss": memory_info.rss,
                    "memory_rss_formatted": self._format_size(memory_info.rss),
                    "memory_vms": memory_info.vms,
                    "memory_vms_formatted": self._format_size(memory_info.vms),
                })
                
                if memory_full_info:
                    proc_info.update({
                        "memory_uss": memory_full_info.uss,
                        "memory_uss_formatted": self._format_size(memory_full_info.uss),
                        "memory_pss": memory_full_info.pss,
                        "memory_pss_formatted": self._format_size(memory_full_info.pss),
                    })
                
                # IO信息
                io_counters = proc.io_counters() if hasattr(proc, 'io_counters') else None
                if io_counters:
                    proc_info.update({
                        "io_read_bytes": io_counters.read_bytes,
                        "io_read_bytes_formatted": self._format_size(io_counters.read_bytes),
                        "io_write_bytes": io_counters.write_bytes,
                        "io_write_bytes_formatted": self._format_size(io_counters.write_bytes),
                    })
                
                # 网络连接
                try:
                    connections = proc.connections()
                    proc_info["connections"] = len(connections)
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    proc_info["connections"] = "未知"
                
                # 线程信息
                try:
                    threads = proc.threads()
                    proc_info["threads"] = len(threads)
                    proc_info["threads_list"] = [{"id": t.id, "user_time": t.user_time, "system_time": t.system_time} 
                                               for t in threads[:10]]  # 只显示前10个线程
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    proc_info["threads"] = "未知"
                
                # 打开的文件
                try:
                    open_files = proc.open_files()
                    proc_info["open_files"] = len(open_files)
                    proc_info["open_files_list"] = [{"path": f.path, "fd": f.fd} for f in open_files[:10]]
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    proc_info["open_files"] = "未知"
            
            return SkillResult(
                success=True,
                message=f"进程信息: {proc_info.get('name')} (PID: {proc_info.get('pid')})",
                data=proc_info
            )
            
        except psutil.NoSuchProcess:
            return SkillResult(
                success=False,
                message=f"进程不存在: {pid or process_name}",
                error="Process does not exist"
            )
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"获取进程信息失败: {str(e)}",
                error=str(e)
            )
    
    async def _search_processes(self, params: Dict[str, Any]) -> SkillResult:
        """搜索进程"""
        search_term = params.get("search_term", "")
        
        if not search_term:
            return SkillResult(
                success=False,
                message="需要搜索关键词",
                error="Search term required"
            )
        
        try:
            results = []
            search_term_lower = search_term.lower()
            
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cmdline']):
                try:
                    proc_info = proc.info
                    
                    # 检查进程名称
                    name = proc_info.get('name', '').lower()
                    # 检查命令行
                    cmdline = proc_info.get('cmdline', [])
                    cmdline_str = ' '.join(cmdline).lower() if cmdline else ''
                    
                    # 检查是否匹配
                    if (search_term_lower in name or 
                        search_term_lower in cmdline_str):
                        
                        # 获取更多信息
                        try:
                            proc_detail = psutil.Process(proc_info.get('pid'))
                            cpu_percent = proc_detail.cpu_percent(interval=0.1)
                            memory_percent = proc_detail.memory_percent()
                            create_time = proc_detail.create_time()
                            
                            results.append({
                                "pid": proc_info.get('pid'),
                                "name": proc_info.get('name'),
                                "user": proc_info.get('username'),
                                "cpu_percent": cpu_percent,
                                "memory_percent": memory_percent,
                                "cmdline": cmdline,
                                "uptime": self._format_duration(datetime.now().timestamp() - create_time),
                                "match_type": "name" if search_term_lower in name else "cmdline"
                            })
                        except:
                            # 如果获取详细信息失败，使用基本信息
                            results.append({
                                "pid": proc_info.get('pid'),
                                "name": proc_info.get('name'),
                                "user": proc_info.get('username'),
                                "cpu_percent": "未知",
                                "memory_percent": "未知",
                                "cmdline": cmdline,
                                "uptime": "未知",
                                "match_type": "name" if search_term_lower in name else "cmdline"
                            })
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return SkillResult(
                success=True,
                message=f"搜索到 {len(results)} 个匹配进程",
                data={
                    "search_term": search_term,
                    "results": results,
                    "total_matches": len(results)
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"搜索进程失败: {str(e)}",
                error=str(e)
            )
    
    async def _kill_process(self, params: Dict[str, Any]) -> SkillResult:
        """终止进程"""
        pid = params.get("pid")
        process_name = params.get("process_name", "")
        signal_name = params.get("signal", "SIGTERM").upper()
        
        if not pid and not process_name:
            return SkillResult(
                success=False,
                message="需要PID或进程名称",
                error="PID or process name required"
            )
        
        # 映射信号名称到信号值
        signal_map = {
            "SIGTERM": signal.SIGTERM,
            "SIGKILL": signal.SIGKILL,
            "SIGINT": signal.SIGINT,
            "SIGHUP": signal.SIGHUP,
            "SIGSTOP": signal.SIGSTOP,
            "SIGCONT": signal.SIGCONT
        }
        
        if signal_name not in signal_map:
            return SkillResult(
                success=False,
                message=f"不支持的信号: {signal_name}",
                error=f"Unsupported signal: {signal_name}"
            )
        
        sig = signal_map[signal_name]
        
        try:
            if pid:
                proc = psutil.Process(pid)
            else:
                # 查找进程
                pids = []
                for p in psutil.process_iter(['pid', 'name']):
                    if p.info.get('name') == process_name:
                        pids.append(p.info.get('pid'))
                
                if not pids:
                    return SkillResult(
                        success=False,
                        message=f"未找到进程: {process_name}",
                        error="Process not found"
                    )
                
                # 使用第一个找到的进程
                proc = psutil.Process(pids[0])
                pid = pids[0]
            
            # 获取进程信息
            proc_name = proc.name()
            proc_user = proc.username()
            
            # 发送信号
            proc.send_signal(sig)
            
            return SkillResult(
                success=True,
                message=f"已发送 {signal_name} 信号到进程 {proc_name} (PID: {pid})",
                data={
                    "pid": pid,
                    "process_name": proc_name,
                    "user": proc_user,
                    "signal": signal_name,
                    "signal_value": sig
                }
            )
            
        except psutil.NoSuchProcess:
            return SkillResult(
                success=False,
                message=f"进程不存在: {pid or process_name}",
                error="Process does not exist"
            )
        except psutil.AccessDenied:
            return SkillResult(
                success=False,
                message="权限不足，无法终止进程",
                error="Permission denied"
            )
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"终止进程失败: {str(e)}",
                error=str(e)
            )
    
    async def _pause_process(self, params: Dict[str, Any]) -> SkillResult:
        """暂停进程"""
        pid = params.get("pid")
        
        if not pid:
            return SkillResult(
                success=False,
                message="需要PID",
                error="PID required"
            )
        
        try:
            proc = psutil.Process(pid)
            proc.suspend()
            
            return SkillResult(
                success=True,
                message=f"已暂停进程 (PID: {pid})",
                data={
                    "pid": pid,
                    "process_name": proc.name(),
                    "action": "pause"
                }
            )
            
        except psutil.NoSuchProcess:
            return SkillResult(
                success=False,
                message=f"进程不存在: {pid}",
                error="Process does not exist"
            )
        except psutil.AccessDenied:
            return SkillResult(
                success=False,
                message="权限不足，无法暂停进程",
                error="Permission denied"
            )
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"暂停进程失败: {str(e)}",
                error=str(e)
            )
    
    async def _resume_process(self, params: Dict[str, Any]) -> SkillResult:
        """恢复进程"""
        pid = params.get("pid")
        
        if not pid:
            return SkillResult(
                success=False,
                message="需要PID",
                error="PID required"
            )
        
        try:
            proc = psutil.Process(pid)
            proc.resume()
            
            return SkillResult(
                success=True,
                message=f"已恢复进程 (PID: {pid})",
                data={
                    "pid": pid,
                    "process_name": proc.name(),
                    "action": "resume"
                }
            )
            
        except psutil.NoSuchProcess:
            return SkillResult(
                success=False,
                message=f"进程不存在: {pid}",
                error="Process does not exist"
            )
        except psutil.AccessDenied:
            return SkillResult(
                success=False,
                message="权限不足，无法恢复进程",
                error="Permission denied"
            )
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"恢复进程失败: {str(e)}",
                error=str(e)
            )
    
    async def _process_tree(self, params: Dict[str, Any]) -> SkillResult:
        """显示进程树"""
        pid = params.get("pid", 1)  # 默认为init进程
        
        try:
            def get_process_tree(p):
                try:
                    proc = psutil.Process(p)
                    children = proc.children(recursive=False)
                    
                    node = {
                        "pid": proc.pid,
                        "name": proc.name(),
                        "user": proc.username(),
                        "cpu_percent": proc.cpu_percent(interval=0.1),
                        "memory_percent": proc.memory_percent(),
                        "children": []
                    }
                    
                    for child in children:
                        node["children"].append(get_process_tree(child.pid))
                    
                    return node
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    return None
            
            tree = get_process_tree(pid)
            if not tree:
                return SkillResult(
                    success=False,
                    message=f"无法获取进程树 (PID: {pid})",
                    error="Cannot get process tree"
                )
            
            # 计算树的大小
            def count_nodes(node):
                if not node:
                    return 0
                count = 1
                for child in node.get("children", []):
                    count += count_nodes(child)
                return count
            
            total_nodes = count_nodes(tree)
            
            return SkillResult(
                success=True,
                message=f"进程树包含 {total_nodes} 个进程",
                data={
                    "tree": tree,
                    "root_pid": pid,
                    "total_processes": total_nodes
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"获取进程树失败: {str(e)}",
                error=str(e)
            )
    
    async def _process_stats(self, params: Dict[str, Any]) -> SkillResult:
        """进程统计信息"""
        try:
            # 系统级统计
            total_processes = len(list(psutil.process_iter()))
            
            # 按用户统计
            users = {}
            for proc in psutil.process_iter(['pid', 'username']):
                try:
                    user = proc.info.get('username')
                    if user:
                        users[user] = users.get(user, 0) + 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # 按状态统计
            statuses = {}
            for proc in psutil.process_iter(['pid', 'status']):
                try:
                    status = proc.info.get('status')
                    if status:
                        statuses[status] = statuses.get(status, 0) + 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # CPU和内存使用统计
            cpu_users = []
            memory_users = []
            
            for proc in psutil.process_iter(['pid', 'name', 'username']):
                try:
                    proc_detail = psutil.Process(proc.info.get('pid'))
                    cpu_percent = proc_detail.cpu_percent(interval=0.1)
                    memory_percent = proc_detail.memory_percent()
                    
                    cpu_users.append({
                        "pid": proc.info.get('pid'),
                        "name": proc.info.get('name'),
                        "user": proc.info.get('username'),
                        "cpu_percent": cpu_percent
                    })
                    
                    memory_users.append({
                        "pid": proc.info.get('pid'),
                        "name": proc.info.get('name'),
                        "user": proc.info.get('username'),
                        "memory_percent": memory_percent
                    })
                except:
                    continue
            
            # 排序
            cpu_users.sort(key=lambda x: x.get("cpu_percent", 0), reverse=True)
            memory_users.sort(key=lambda x: x.get("memory_percent", 0), reverse=True)
            
            # 系统信息
            system_cpu = psutil.cpu_percent(interval=0.1)
            system_memory = psutil.virtual_memory().percent
            boot_time = datetime.fromtimestamp(psutil.boot_time()).isoformat()
            
            return SkillResult(
                success=True,
                message="进程统计信息",
                data={
                    "total_processes": total_processes,
                    "users": users,
                    "statuses": statuses,
                    "top_cpu_processes": cpu_users[:10],
                    "top_memory_processes": memory_users[:10],
                    "system_cpu": system_cpu,
                    "system_memory": system_memory,
                    "boot_time": boot_time,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"获取进程统计失败: {str(e)}",
                error=str(e)
            )
    
    async def _monitor_processes(self, params: Dict[str, Any]) -> SkillResult:
        """监控进程"""
        cpu_threshold = params.get("cpu_threshold", 80.0)
        memory_threshold = params.get("memory_threshold", 80.0)
        duration = params.get("duration", 60)  # 秒
        
        if duration > 300:  # 限制最大监控时间
            duration = 300
        
        try:
            import time
            alerts = []
            
            start_time = time.time()
            end_time = start_time + duration
            
            while time.time() < end_time:
                # 检查所有进程
                for proc in psutil.process_iter(['pid', 'name', 'username']):
                    try:
                        proc_detail = psutil.Process(proc.info.get('pid'))
                        cpu_percent = proc_detail.cpu_percent(interval=0.1)
                        memory_percent = proc_detail.memory_percent()
                        
                        # 检查阈值
                        if cpu_percent > cpu_threshold:
                            alerts.append({
                                "timestamp": datetime.now().isoformat(),
                                "type": "cpu",
                                "pid": proc.info.get('pid'),
                                "name": proc.info.get('name'),
                                "user": proc.info.get('username'),
                                "value": cpu_percent,
                                "threshold": cpu_threshold
                            })
                        
                        if memory_percent > memory_threshold:
                            alerts.append({
                                "timestamp": datetime.now().isoformat(),
                                "type": "memory",
                                "pid": proc.info.get('pid'),
                                "name": proc.info.get('name'),
                                "user": proc.info.get('username'),
                                "value": memory_percent,
                                "threshold": memory_threshold
                            })
                            
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                # 短暂休眠
                time.sleep(2)
            
            # 统计
            cpu_alerts = [a for a in alerts if a["type"] == "cpu"]
            memory_alerts = [a for a in alerts if a["type"] == "memory"]
            
            # 去重（同一进程多次告警）
            unique_cpu = {}
            for alert in cpu_alerts:
                key = f"{alert['pid']}-{alert['name']}"
                if key not in unique_cpu or alert['value'] > unique_cpu[key]['value']:
                    unique_cpu[key] = alert
            
            unique_memory = {}
            for alert in memory_alerts:
                key = f"{alert['pid']}-{alert['name']}"
                if key not in unique_memory or alert['value'] > unique_memory[key]['value']:
                    unique_memory[key] = alert
            
            return SkillResult(
                success=True,
                message=f"监控完成，发现 {len(unique_cpu)} 个CPU告警，{len(unique_memory)} 个内存告警",
                data={
                    "duration": duration,
                    "cpu_threshold": cpu_threshold,
                    "memory_threshold": memory_threshold,
                    "cpu_alerts": list(unique_cpu.values()),
                    "memory_alerts": list(unique_memory.values()),
                    "total_alerts": len(unique_cpu) + len(unique_memory),
                    "start_time": datetime.fromtimestamp(start_time).isoformat(),
                    "end_time": datetime.fromtimestamp(end_time).isoformat()
                }
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                message=f"进程监控失败: {str(e)}",
                error=str(e)
            )
    
    def _format_duration(self, seconds: float) -> str:
        """格式化时间间隔"""
        if seconds < 60:
            return f"{seconds:.1f}秒"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}分钟"
        elif seconds < 86400:
            hours = seconds / 3600
            return f"{hours:.1f}小时"
        else:
            days = seconds / 86400
            return f"{days:.1f}天"
    
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