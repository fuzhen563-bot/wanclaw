"""
WanClaw IM适配器主程序
提供统一的多平台IM消息收发服务
"""

import asyncio
import logging
import signal
import sys
import yaml
from pathlib import Path
from typing import Dict, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('im_adapter.log')
    ]
)

logger = logging.getLogger(__name__)

# 导入适配器模块
try:
    from gateway import get_gateway, IMGateway
    from models.message import UnifiedMessage, PlatformType, MessageType
    from adapters.wecom import WeComAdapter
    from adapters.feishu import FeishuAdapter
    from adapters.qq import QQAdapter
    from adapters.wechat import WeChatAdapter
    from adapters.telegram import TelegramAdapter
except ImportError as e:
    try:
        from wanclaw.backend.im_adapter.gateway import get_gateway, IMGateway
        from wanclaw.backend.im_adapter.models.message import UnifiedMessage, PlatformType, MessageType
        from wanclaw.backend.im_adapter.adapters.wecom import WeComAdapter
        from wanclaw.backend.im_adapter.adapters.feishu import FeishuAdapter
        from wanclaw.backend.im_adapter.adapters.qq import QQAdapter
        from wanclaw.backend.im_adapter.adapters.wechat import WeChatAdapter
        from wanclaw.backend.im_adapter.adapters.telegram import TelegramAdapter
    except ImportError:
        logger.error(f"导入模块失败: {e}")
        logger.error("请确保所有适配器模块已正确安装")
        sys.exit(1)


class IMAdapterService:
    """IM适配器服务"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.config = None
        self.gateway = None
        self.running = False
        
    def load_config(self) -> bool:
        """加载配置文件"""
        try:
            config_file = Path(self.config_path)
            if not config_file.exists():
                logger.error(f"配置文件不存在: {self.config_path}")
                return False
            
            with open(config_file, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            
            logger.info(f"配置文件加载成功: {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return False
    
    async def setup_adapters(self):
        """设置所有适配器"""
        try:
            self.gateway = get_gateway()
            
            # 企业微信适配器
            wecom_config = self.config.get('wecom', {})
            if wecom_config.get('enabled'):
                logger.info("设置企业微信适配器...")
                self.gateway.create_and_register(
                    PlatformType.WECOM,
                    wecom_config
                )
            
            # 飞书适配器
            feishu_config = self.config.get('feishu', {})
            if feishu_config.get('enabled'):
                logger.info("设置飞书适配器...")
                self.gateway.create_and_register(
                    PlatformType.FEISHU,
                    feishu_config
                )
            
            # QQ适配器
            qq_config = self.config.get('qq', {})
            if qq_config.get('enabled'):
                logger.info("设置QQ适配器...")
                self.gateway.create_and_register(
                    PlatformType.QQ,
                    qq_config
                )
            
            # 微信适配器
            wechat_config = self.config.get('wechat', {})
            if wechat_config.get('enabled'):
                logger.info("设置微信适配器...")
                self.gateway.create_and_register(
                    PlatformType.WECHAT,
                    wechat_config
                )
            
            # Telegram适配器
            telegram_config = self.config.get('telegram', {})
            if telegram_config.get('enabled'):
                logger.info("设置Telegram适配器...")
                self.gateway.create_and_register(
                    PlatformType.TELEGRAM,
                    telegram_config
                )
            
            logger.info(f"已设置 {len(self.gateway.adapters)} 个适配器")
            return True
            
        except Exception as e:
            logger.error(f"设置适配器失败: {e}")
            return False
    
    async def start(self):
        """启动服务"""
        if self.running:
            logger.warning("服务已经在运行")
            return
        
        logger.info("启动IM适配器服务...")
        
        # 加载配置
        if not self.load_config():
            logger.error("配置加载失败，服务启动中止")
            return
        
        # 设置适配器
        if not await self.setup_adapters():
            logger.error("适配器设置失败，服务启动中止")
            return
        
        # 注册消息处理器
        self.gateway.register_message_handler(self._handle_message)
        self.gateway.register_error_handler(self._handle_error)
        
        # 启动网关
        await self.gateway.start()
        
        # 设置信号处理
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))
        
        self.running = True
        logger.info("IM适配器服务启动成功")
        
        # 保持运行
        try:
            while self.running:
                await asyncio.sleep(1)
                
                # 定期健康检查
                health = await self.gateway.health_check()
                if not health.get("running", False):
                    logger.warning("网关运行状态异常")
                    
        except asyncio.CancelledError:
            logger.info("服务被取消")
        except Exception as e:
            logger.error(f"服务运行异常: {e}")
        finally:
            await self.stop()
    
    async def _handle_message(self, message: UnifiedMessage):
        """处理接收到的消息"""
        try:
            logger.info(f"收到消息 [{message.platform}/{message.chat_id}]: {message.text[:100]}...")
            
            # 这里可以添加消息处理逻辑
            # 例如：转发到其他平台、执行命令、保存到数据库等
            
            # 示例：如果是命令，回复帮助信息
            if message.is_command:
                command = message.get_command()
                if command == "help":
                    help_text = """
                    可用命令：
                    /help - 显示帮助信息
                    /status - 查看服务状态
                    /echo <text> - 回复文本
                    /broadcast <text> - 广播消息到所有平台
                    """
                    
                    await self.gateway.send_message(
                        platform=message.platform,
                        chat_id=message.chat_id,
                        content=help_text,
                        message_type=MessageType.TEXT
                    )
                    
                elif command == "status":
                    status = await self.gateway.health_check()
                    status_text = f"服务状态：\n"
                    status_text += f"运行中：{'是' if status['running'] else '否'}\n"
                    status_text += f"适配器数量：{status['adapter_count']}\n"
                    status_text += f"运行时间：{status['uptime']:.1f}秒\n"
                    
                    for platform, adapter_status in status.get('adapters', {}).items():
                        connected = adapter_status.get('connected', False)
                        status_text += f"{platform}: {'✅' if connected else '❌'}\n"
                    
                    await self.gateway.send_message(
                        platform=message.platform,
                        chat_id=message.chat_id,
                        content=status_text,
                        message_type=MessageType.TEXT
                    )
                    
                elif command == "echo":
                    args = message.get_command_args()
                    if args:
                        await self.gateway.send_message(
                            platform=message.platform,
                            chat_id=message.chat_id,
                            content=" ".join(args),
                            message_type=MessageType.TEXT
                        )
                    
                elif command == "broadcast":
                    args = message.get_command_args()
                    if args:
                        broadcast_text = " ".join(args)
                        platforms = list(self.gateway.adapters.keys())
                        
                        # 广播到所有适配器
                        for platform in platforms:
                            adapter = self.gateway.get_adapter(platform)
                            if adapter and adapter.is_connected:
                                # 这里需要知道每个适配器的默认聊天ID
                                # 实际应用中应该从配置或数据库获取
                                logger.info(f"广播消息到 {platform}")
            
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
    
    async def _handle_error(self, error: Exception):
        """处理错误"""
        logger.error(f"IM适配器错误: {error}")
        # 这里可以添加错误处理逻辑，如发送告警、重试等
    
    async def stop(self):
        """停止服务"""
        if not self.running:
            return
        
        logger.info("停止IM适配器服务...")
        self.running = False
        
        if self.gateway:
            await self.gateway.stop()
        
        logger.info("IM适配器服务已停止")
    
    async def send_test_message(self):
        """发送测试消息（用于测试）"""
        if not self.gateway or not self.gateway.is_running:
            logger.error("网关未运行")
            return
        
        # 向所有已连接的适配器发送测试消息
        for platform, adapter in self.gateway.adapters.items():
            if adapter.is_connected:
                logger.info(f"向 {platform} 发送测试消息...")
                
                # 这里需要指定聊天ID
                # 实际应用中应该从配置或数据库获取
                chat_id = "test_chat_id"  # 替换为实际的聊天ID
                
                response = await self.gateway.send_message(
                    platform=platform,
                    chat_id=chat_id,
                    content=f"测试消息来自 {platform} 适配器",
                    message_type=MessageType.TEXT
                )
                
                if response.success:
                    logger.info(f"测试消息发送成功: {platform}")
                else:
                    logger.error(f"测试消息发送失败: {platform} - {response.error}")


async def main():
    """主函数"""
    # 创建服务实例
    service = IMAdapterService()
    
    # 启动服务
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("收到键盘中断信号")
    except Exception as e:
        logger.error(f"服务异常终止: {e}")
    finally:
        await service.stop()


if __name__ == "__main__":
    # 解析命令行参数
    import argparse
    
    parser = argparse.ArgumentParser(description="WanClaw IM适配器服务")
    parser.add_argument("--config", "-c", default="config/config.yaml", help="配置文件路径")
    parser.add_argument("--test", "-t", action="store_true", help="发送测试消息")
    parser.add_argument("--health", action="store_true", help="检查服务健康状态")
    
    args = parser.parse_args()
    
    if args.health:
        # 健康检查模式
        async def health_check():
            service = IMAdapterService(args.config)
            if service.load_config():
                print("配置加载成功")
                if await service.setup_adapters():
                    print("适配器设置成功")
                    health = await service.gateway.health_check()
                    print(yaml.dump(health, default_flow_style=False))
                else:
                    print("适配器设置失败")
            else:
                print("配置加载失败")
        
        asyncio.run(health_check())
        
    elif args.test:
        # 测试模式
        async def test_mode():
            service = IMAdapterService(args.config)
            if service.load_config() and await service.setup_adapters():
                await service.gateway.start()
                await service.send_test_message()
                await service.gateway.stop()
        
        asyncio.run(test_mode())
        
    else:
        # 正常启动模式
        asyncio.run(main())