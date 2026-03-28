#!/usr/bin/env python3
"""
WanClaw 系统监控脚本
监控系统健康状况和性能指标
"""

import os
import sys
import time
import json
import psutil
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "wanclaw"))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/monitor.log')
    ]
)

logger = logging.getLogger(__name__)


class SystemMonitor:
    """系统监控器"""
    
    def __init__(self):
        self.metrics_file = Path("logs/metrics.json")
        self.health_file = Path("logs/health.json")
        
        # 创建日志目录
        self.metrics_file.parent.mkdir(exist_ok=True)
        
        # 初始化指标
        self.metrics = {
            "start_time": datetime.now().isoformat(),
            "system_checks": 0,
            "skill_checks": 0,
            "adapter_checks": 0,
            "errors": 0,
            "last_check": None
        }
    
    async def check_system_resources(self) -> Dict[str, Any]:
        """检查系统资源"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            processes = len(psutil.pids())
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_total_gb": memory.total / (1024**3),
                "memory_available_gb": memory.available / (1024**3),
                "disk_percent": disk.percent,
                "disk_total_gb": disk.total / (1024**3),
                "disk_free_gb": disk.free / (1024**3),
                "process_count": processes,
                "timestamp": datetime.now().isoformat(),
                "status": "healthy"
            }
        except Exception as e:
            logger.error(f"系统资源检查失败: {e}")
            return {
                "error": str(e),
                "status": "error",
                "timestamp": datetime.now().isoformat()
            }
    
    async def check_skill_system(self) -> Dict[str, Any]:
        """检查技能系统"""
        try:
            from wanclaw.backend.skills import SkillManager
            
            skill_manager = SkillManager()
            skills = skill_manager.list_skills()
            
            return {
                "skill_count": len(skills),
                "skills": [skill["name"] for skill in skills],
                "status": "healthy" if skills else "warning",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"技能系统检查失败: {e}")
            return {
                "error": str(e),
                "status": "error",
                "timestamp": datetime.now().isoformat()
            }
    
    async def check_adapters(self) -> Dict[str, Any]:
        """检查适配器"""
        try:
            import yaml
            
            config_path = Path("wanclaw/backend/im_adapter/config/config.yaml")
            if not config_path.exists():
                return {
                    "error": "配置文件不存在",
                    "status": "error",
                    "timestamp": datetime.now().isoformat()
                }
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            enabled_adapters = []
            for platform in ["wecom", "feishu", "qq", "wechat", "telegram"]:
                if config.get(platform, {}).get("enabled", False):
                    enabled_adapters.append(platform)
            
            return {
                "enabled_adapters": enabled_adapters,
                "total_adapters": len(enabled_adapters),
                "status": "healthy" if enabled_adapters else "warning",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"适配器检查失败: {e}")
            return {
                "error": str(e),
                "status": "error",
                "timestamp": datetime.now().isoformat()
            }
    
    async def check_log_files(self) -> Dict[str, Any]:
        """检查日志文件"""
        try:
            log_dir = Path("logs")
            if not log_dir.exists():
                return {
                    "error": "日志目录不存在",
                    "status": "warning",
                    "timestamp": datetime.now().isoformat()
                }
            
            log_files = []
            total_size = 0
            for log_file in log_dir.glob("*.log"):
                size_mb = log_file.stat().st_size / (1024 * 1024)
                log_files.append({
                    "name": log_file.name,
                    "size_mb": round(size_mb, 2),
                    "modified": datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
                })
                total_size += size_mb
            
            return {
                "log_files": log_files,
                "total_size_mb": round(total_size, 2),
                "file_count": len(log_files),
                "status": "healthy",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"日志文件检查失败: {e}")
            return {
                "error": str(e),
                "status": "error",
                "timestamp": datetime.now().isoformat()
            }
    
    async def run_health_check(self) -> Dict[str, Any]:
        """运行健康检查"""
        logger.info("开始系统健康检查...")
        
        checks = {
            "system_resources": await self.check_system_resources(),
            "skill_system": await self.check_skill_system(),
            "adapters": await self.check_adapters(),
            "log_files": await self.check_log_files(),
        }
        
        # 计算总体状态
        statuses = [check["status"] for check in checks.values()]
        if "error" in statuses:
            overall_status = "error"
        elif "warning" in statuses:
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        health_report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "healthy_checks": statuses.count("healthy"),
                "warning_checks": statuses.count("warning"),
                "error_checks": statuses.count("error")
            }
        }
        
        # 保存健康报告
        with open(self.health_file, 'w', encoding='utf-8') as f:
            json.dump(health_report, f, indent=2, ensure_ascii=False)
        
        # 更新指标
        self.metrics["system_checks"] += 1
        self.metrics["skill_checks"] += 1
        self.metrics["adapter_checks"] += 1
        self.metrics["errors"] += statuses.count("error")
        self.metrics["last_check"] = datetime.now().isoformat()
        
        # 保存指标
        with open(self.metrics_file, 'w', encoding='utf-8') as f:
            json.dump(self.metrics, f, indent=2, ensure_ascii=False)
        
        logger.info(f"健康检查完成: {overall_status}")
        return health_report
    
    def print_health_summary(self, health_report: Dict[str, Any]):
        """打印健康检查摘要"""
        print("\n" + "=" * 60)
        print("📊 WanClaw 系统健康报告")
        print("=" * 60)
        print(f"检查时间: {health_report['timestamp']}")
        print(f"总体状态: {health_report['overall_status'].upper()}")
        
        summary = health_report["summary"]
        print(f"\n📋 检查摘要:")
        print(f"   总检查数: {summary['total_checks']}")
        print(f"   健康检查: {summary['healthy_checks']} ✅")
        print(f"   警告检查: {summary['warning_checks']} ⚠️")
        print(f"   错误检查: {summary['error_checks']} ❌")
        
        print(f"\n🔍 详细检查:")
        for check_name, check_result in health_report["checks"].items():
            status_icon = "✅" if check_result["status"] == "healthy" else "⚠️" if check_result["status"] == "warning" else "❌"
            print(f"   {check_name}: {status_icon} {check_result['status']}")
            
            if check_name == "system_resources" and check_result["status"] == "healthy":
                print(f"      CPU: {check_result['cpu_percent']}%")
                print(f"      内存: {check_result['memory_percent']}% ({check_result['memory_available_gb']:.1f} GB可用)")
                print(f"      磁盘: {check_result['disk_percent']}% ({check_result['disk_free_gb']:.1f} GB可用)")
            
            elif check_name == "skill_system" and check_result["status"] == "healthy":
                print(f"      技能数量: {check_result['skill_count']}")
            
            elif check_name == "adapters" and check_result["status"] == "healthy":
                print(f"      启用的适配器: {', '.join(check_result['enabled_adapters'])}")
            
            elif "error" in check_result:
                print(f"      错误: {check_result['error']}")
        
        print("\n💡 建议:")
        if health_report['overall_status'] == 'healthy':
            print("   系统运行正常，无需操作")
        elif health_report['overall_status'] == 'warning':
            print("   系统存在警告，建议检查日志文件")
        else:
            print("   系统存在错误，需要立即处理")
        
        print("=" * 60)


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="WanClaw 系统监控")
    parser.add_argument("--interval", type=int, default=0, 
                       help="监控间隔（秒），0表示单次运行")
    parser.add_argument("--daemon", action="store_true",
                       help="以守护进程模式运行")
    
    args = parser.parse_args()
    
    monitor = SystemMonitor()
    
    if args.daemon or args.interval > 0:
        logger.info(f"启动监控守护进程，间隔: {args.interval}秒")
        
        try:
            while True:
                health_report = await monitor.run_health_check()
                
                if args.daemon:
                    # 守护进程模式只记录日志
                    logger.info(f"健康检查完成: {health_report['overall_status']}")
                else:
                    # 交互模式显示报告
                    monitor.print_health_summary(health_report)
                
                if args.interval > 0:
                    await asyncio.sleep(args.interval)
                else:
                    # 守护进程默认30秒检查一次
                    await asyncio.sleep(30)
                    
        except KeyboardInterrupt:
            logger.info("监控守护进程停止")
    else:
        # 单次运行模式
        health_report = await monitor.run_health_check()
        monitor.print_health_summary(health_report)


if __name__ == "__main__":
    asyncio.run(main())