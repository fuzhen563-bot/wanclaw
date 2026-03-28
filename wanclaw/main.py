#!/usr/bin/env python3
"""
WanClaw 主入口脚本
启动所有核心服务
"""

import asyncio
import argparse
import logging
import signal
import sys
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WanClawRunner:
    """WanClaw 运行器"""
    
    def __init__(self):
        self.tasks = []
        self.gateway = None
        self.running = False
    
    async def start_gateway(self):
        """启动分布式Gateway"""
        try:
            from wanclaw.backend.gateway import get_distributed_gateway
            
            self.gateway = await get_distributed_gateway(
                redis_url=os.environ.get("WANCLAW_REDIS_URL", "redis://localhost:6379"),
                node_id=f"node-{os.environ.get('HOSTNAME', 'local')}",
                cluster_name="wanclaw",
            )
            logger.info("Distributed Gateway started")
        except Exception as e:
            logger.warning(f"Gateway start failed (Redis may not be available): {e}")
    
    async def start_task_queue(self):
        """启动任务队列"""
        try:
            from wanclaw.backend.tasks import get_task_queue, get_task_executor
            
            queue = await get_task_queue(
                redis_url=os.environ.get("WANCLAW_REDIS_URL", "redis://localhost:6379"),
            )
            executor = await get_task_executor(
                redis_url=os.environ.get("WANCLAW_REDIS_URL", "redis://localhost:6379"),
            )
            
            await executor.start()
            logger.info("Task Queue started")
        except Exception as e:
            logger.warning(f"Task Queue start failed: {e}")
    
    async def start_notification(self):
        """启动通知服务"""
        try:
            from wanclaw.backend.notification import get_notification_manager
            
            notifier = get_notification_manager()
            logger.info("Notification Manager initialized")
        except Exception as e:
            logger.warning(f"Notification start failed: {e}")
    
    async def start_analytics(self):
        """启动分析服务"""
        try:
            from wanclaw.backend.analytics import get_analytics, get_revenue_analytics
            
            analytics = await get_analytics()
            revenue = await get_revenue_analytics()
            logger.info("Analytics services initialized")
        except Exception as e:
            logger.warning(f"Analytics start failed: {e}")
    
    async def start_workflow_scheduler(self):
        """启动工作流调度器"""
        try:
            from wanclaw.backend.workflows import get_workflow_engine
            
            engine = get_workflow_engine()
            await engine.start_scheduler()
            logger.info("Workflow scheduler started")
        except Exception as e:
            logger.warning(f"Workflow scheduler start failed: {e}")
    
    async def start_alert_monitor(self):
        """启动告警监控"""
        try:
            from wanclaw.backend.notification import get_alert_monitor
            
            monitor = await get_alert_monitor()
            logger.info("Alert monitor started")
        except Exception as e:
            logger.warning(f"Alert monitor start failed: {e}")
    
    async def start_all(self):
        """启动所有服务"""
        self.running = True
        
        logger.info("Starting WanClaw services...")
        
        # 并行启动所有服务
        await asyncio.gather(
            self.start_gateway(),
            self.start_task_queue(),
            self.start_notification(),
            self.start_analytics(),
            self.start_workflow_scheduler(),
            self.start_alert_monitor(),
        )
        
        logger.info("All services started successfully")
        
        # 保持运行
        while self.running:
            await asyncio.sleep(10)
    
    async def stop_all(self):
        """停止所有服务"""
        logger.info("Stopping WanClaw services...")
        self.running = False
        
        if self.gateway:
            await self.gateway.close()
        
        logger.info("All services stopped")


async def main():
    parser = argparse.ArgumentParser(description="WanClaw Main Entry")
    parser.add_argument("--mode", choices=["all", "gateway", "tasks", "workflow", "api"], 
                        default="all", help="Service mode to run")
    parser.add_argument("--redis-url", default="redis://localhost:6379",
                        help="Redis URL")
    args = parser.parse_args()
    
    runner = WanClawRunner()
    
    # 处理信号
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        asyncio.create_task(runner.stop_all())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if args.mode == "all":
            await runner.start_all()
        elif args.mode == "gateway":
            await runner.start_gateway()
        elif args.mode == "tasks":
            await runner.start_task_queue()
        elif args.mode == "workflow":
            await runner.start_workflow_scheduler()
        elif args.mode == "api":
            logger.info("API mode - use uvicorn to start the API server")
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
