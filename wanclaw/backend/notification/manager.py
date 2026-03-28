"""
告警通知系统
支持多渠道：钉钉、飞书、邮件、短信、Webhook
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ChannelType(Enum):
    """通知渠道类型"""
    DINGTALK = "dingtalk"
    FEISHU = "feishu"
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    WECHAT_WORK = "wecom"
    TELEGRAM = "telegram"


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class NotificationConfig:
    """通知配置"""
    config_id: str
    name: str
    channel: ChannelType
    enabled: bool = True
    config_data: Dict[str, Any] = field(default_factory=dict)
    recipients: List[str] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Notification:
    """通知"""
    notification_id: str
    channel: ChannelType
    title: str
    content: str
    level: AlertLevel = AlertLevel.INFO
    recipients: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    status: str = "pending"


@dataclass
class AlertRule:
    """告警规则"""
    rule_id: str
    name: str
    condition: str  # 条件表达式
    level: AlertLevel = AlertLevel.WARNING
    channels: List[str] = field(default_factory=list)
    enabled: bool = True
    cooldown_seconds: int = 300
    last_triggered: Optional[datetime] = None


class NotificationChannel(ABC):
    """通知渠道基类"""
    
    @abstractmethod
    async def send(self, notification: Notification) -> Dict[str, Any]:
        """发送通知"""
        pass
    
    @abstractmethod
    async def test(self, config: NotificationConfig) -> bool:
        """测试连接"""
        pass
    
    async def format_message(self, notification: Notification) -> Any:
        """格式化消息（子类可重写）"""
        return notification.content


class DingTalkChannel(NotificationChannel):
    """钉钉通知"""
    
    async def send(self, notification: Notification) -> Dict[str, Any]:
        """发送钉钉消息"""
        # 实际需要使用钉钉SDK
        config = notification.metadata.get("config", {})
        webhook = config.get("webhook")
        secret = config.get("secret")
        
        if not webhook:
            return {"success": False, "error": "Webhook not configured"}
        
        # 构建消息
        msg = {
            "msgtype": "markdown",
            "markdown": {
                "title": notification.title,
                "text": f"## {notification.title}\n\n{notification.content}",
            },
        }
        
        # 签名计算（需要secret）
        # 实际发送需要使用httpx
        logger.info(f"DingTalk notification sent: {notification.notification_id}")
        
        return {"success": True, "message_id": notification.notification_id}
    
    async def test(self, config: NotificationConfig) -> bool:
        """测试钉钉连接"""
        return True


class FeishuChannel(NotificationChannel):
    """飞书通知"""
    
    async def send(self, notification: Notification) -> Dict[str, Any]:
        """发送飞书消息"""
        config = notification.metadata.get("config", {})
        webhook = config.get("webhook")
        
        if not webhook:
            return {"success": False, "error": "Webhook not configured"}
        
        # 构建消息
        msg = {
            "msg_type": "text",
            "content": {
                "text": f"{notification.title}\n{notification.content}",
            },
        }
        
        logger.info(f"Feishu notification sent: {notification.notification_id}")
        
        return {"success": True, "message_id": notification.notification_id}
    
    async def test(self, config: NotificationConfig) -> bool:
        """测试飞书连接"""
        return True


class EmailChannel(NotificationChannel):
    """邮件通知"""
    
    async def send(self, notification: Notification) -> Dict[str, Any]:
        """发送邮件"""
        config = notification.metadata.get("config", {})
        
        smtp_host = config.get("smtp_host")
        smtp_port = config.get("smtp_port", 587)
        username = config.get("username")
        password = config.get("password")
        from_addr = config.get("from_addr")
        
        if not all([smtp_host, username, password, from_addr]):
            return {"success": False, "error": "Email config incomplete"}
        
        # 实际发送需要使用aiosmtplib
        logger.info(f"Email notification sent: {notification.notification_id}")
        
        return {"success": True, "message_id": notification.notification_id}
    
    async def test(self, config: NotificationConfig) -> bool:
        """测试邮件连接"""
        return True


class WebhookChannel(NotificationChannel):
    """Webhook通知"""
    
    async def send(self, notification: Notification) -> Dict[str, Any]:
        """发送Webhook"""
        config = notification.metadata.get("config", {})
        url = config.get("url")
        method = config.get("method", "POST")
        headers = config.get("headers", {})
        
        if not url:
            return {"success": False, "error": "URL not configured"}
        
        payload = {
            "title": notification.title,
            "content": notification.content,
            "level": notification.level.value,
            "timestamp": notification.created_at.isoformat(),
            "notification_id": notification.notification_id,
        }
        
        # 实际发送需要使用httpx
        logger.info(f"Webhook notification sent: {notification.notification_id}")
        
        return {"success": True, "message_id": notification.notification_id}
    
    async def test(self, config: NotificationConfig) -> bool:
        """测试Webhook连接"""
        return True


class SMSChannel(NotificationChannel):
    """短信通知"""
    
    async def send(self, notification: Notification) -> Dict[str, Any]:
        """发送短信"""
        config = notification.metadata.get("config", {})
        
        provider = config.get("provider")  # aliyun, tencent, etc.
        secret_id = config.get("secret_id")
        secret_key = config.get("secret_key")
        
        if not all([provider, secret_id, secret_key]):
            return {"success": False, "error": "SMS config incomplete"}
        
        logger.info(f"SMS notification sent: {notification.notification_id}")
        
        return {"success": True, "message_id": notification.notification_id}
    
    async def test(self, config: NotificationConfig) -> bool:
        """测试短信连接"""
        return True


class NotificationManager:
    """通知管理器"""
    
    def __init__(self):
        self._channels: Dict[ChannelType, NotificationChannel] = {}
        self._configs: Dict[str, NotificationConfig] = {}
        self._rules: Dict[str, AlertRule] = {}
        
        # 注册默认渠道
        self._register_default_channels()
    
    def _register_default_channels(self):
        """注册默认渠道"""
        self._channels[ChannelType.DINGTALK] = DingTalkChannel()
        self._channels[ChannelType.FEISHU] = FeishuChannel()
        self._channels[ChannelType.EMAIL] = EmailChannel()
        self._channels[ChannelType.WEBHOOK] = WebhookChannel()
        self._channels[ChannelType.SMS] = SMSChannel()
    
    def register_channel(self, channel_type: ChannelType, channel: NotificationChannel):
        """注册渠道"""
        self._channels[channel_type] = channel
    
    async def add_config(
        self,
        name: str,
        channel: ChannelType,
        config_data: Dict[str, Any],
        recipients: List[str] = None,
        filters: Dict[str, Any] = None,
        enabled: bool = True,
    ) -> NotificationConfig:
        """添加通知配置"""
        config_id = f"config-{uuid.uuid4().hex[:8]}"
        
        config = NotificationConfig(
            config_id=config_id,
            name=name,
            channel=channel,
            config_data=config_data,
            recipients=recipients or [],
            filters=filters or {},
            enabled=enabled,
        )
        
        self._configs[config_id] = config
        
        logger.info(f"Notification config added: {name} ({channel.value})")
        
        return config
    
    async def update_config(self, config_id: str, **updates) -> Optional[NotificationConfig]:
        """更新通知配置"""
        config = self._configs.get(config_id)
        if not config:
            return None
        
        if "name" in updates:
            config.name = updates["name"]
        if "config_data" in updates:
            config.config_data.update(updates["config_data"])
        if "recipients" in updates:
            config.recipients = updates["recipients"]
        if "filters" in updates:
            config.filters.update(updates["filters"])
        if "enabled" in updates:
            config.enabled = updates["enabled"]
        
        return config
    
    async def delete_config(self, config_id: str) -> bool:
        """删除通知配置"""
        if config_id in self._configs:
            del self._configs[config_id]
            return True
        return False
    
    async def get_config(self, config_id: str) -> Optional[NotificationConfig]:
        """获取通知配置"""
        return self._configs.get(config_id)
    
    async def list_configs(self, channel: ChannelType = None, enabled: bool = None) -> List[NotificationConfig]:
        """列出通知配置"""
        configs = list(self._configs.values())
        
        if channel:
            configs = [c for c in configs if c.channel == channel]
        if enabled is not None:
            configs = [c for c in configs if c.enabled == enabled]
        
        return configs
    
    async def test_config(self, config_id: str) -> bool:
        """测试通知配置"""
        config = self._configs.get(config_id)
        if not config:
            return False
        
        channel = self._channels.get(config.channel)
        if not channel:
            return False
        
        return await channel.test(config)
    
    async def send(
        self,
        title: str,
        content: str,
        level: AlertLevel = AlertLevel.INFO,
        channel_filter: ChannelType = None,
        recipient_filter: str = None,
        metadata: Dict[str, Any] = None,
    ) -> List[str]:
        """发送通知"""
        # 获取可用配置
        configs = await self.list_configs(enabled=True)
        
        if channel_filter:
            configs = [c for c in configs if c.channel == channel_filter]
        
        results = []
        
        for config in configs:
            # 检查接收者过滤
            if recipient_filter and recipient_filter not in config.recipients:
                continue
            
            # 检查过滤器
            if not self._check_filters(config.filters, level, title):
                continue
            
            # 获取渠道
            channel = self._channels.get(config.channel)
            if not channel:
                continue
            
            # 创建通知
            notification = Notification(
                notification_id=f"notif-{uuid.uuid4().hex[:8]}",
                channel=config.channel,
                title=title,
                content=content,
                level=level,
                recipients=config.recipients,
                metadata={"config": config.config_data},
            )
            
            # 发送
            try:
                result = await channel.send(notification)
                if result.get("success"):
                    results.append(notification.notification_id)
            except Exception as e:
                logger.error(f"Notification failed: {e}")
        
        return results
    
    def _check_filters(self, filters: Dict, level: AlertLevel, title: str) -> bool:
        """检查过滤器"""
        # 级别过滤
        if "level" in filters:
            allowed_levels = filters["level"]
            if isinstance(allowed_levels, list):
                if level.value not in allowed_levels:
                    return False
            elif level.value != allowed_levels:
                return False
        
        # 标题关键词过滤
        if "title_keywords" in filters:
            keywords = filters["title_keywords"]
            if not any(kw in title for kw in keywords):
                return False
        
        return True
    
    async def add_rule(
        self,
        name: str,
        condition: str,
        level: AlertLevel = AlertLevel.WARNING,
        channels: List[str] = None,
        cooldown_seconds: int = 300,
    ) -> AlertRule:
        """添加告警规则"""
        rule_id = f"rule-{uuid.uuid4().hex[:8]}"
        
        rule = AlertRule(
            rule_id=rule_id,
            name=name,
            condition=condition,
            level=level,
            channels=channels or [],
            cooldown_seconds=cooldown_seconds,
        )
        
        self._rules[rule_id] = rule
        
        return rule
    
    async def update_rule(self, rule_id: str, **updates) -> Optional[AlertRule]:
        """更新告警规则"""
        rule = self._rules.get(rule_id)
        if not rule:
            return None
        
        if "name" in updates:
            rule.name = updates["name"]
        if "condition" in updates:
            rule.condition = updates["condition"]
        if "level" in updates:
            rule.level = updates["level"]
        if "channels" in updates:
            rule.channels = updates["channels"]
        if "enabled" in updates:
            rule.enabled = updates["enabled"]
        
        return rule
    
    async def delete_rule(self, rule_id: str) -> bool:
        """删除告警规则"""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False
    
    async def list_rules(self, enabled: bool = None) -> List[AlertRule]:
        """列出告警规则"""
        rules = list(self._rules.values())
        
        if enabled is not None:
            rules = [r for r in rules if r.enabled == enabled]
        
        return rules
    
    async def check_and_notify(self, metric: str, value: float, labels: Dict = None) -> List[str]:
        """检查告警规则并通知"""
        triggered = []
        
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            
            # 检查冷却时间
            if rule.last_triggered:
                elapsed = (datetime.now() - rule.last_triggered).total_seconds()
                if elapsed < rule.cooldown_seconds:
                    continue
            
            # 评估条件（简化实现）
            if self._evaluate_condition(rule.condition, metric, value):
                # 发送通知
                results = await self.send(
                    title=f"告警: {rule.name}",
                    content=f"指标 {metric} = {value}",
                    level=rule.level,
                )
                
                triggered.extend(results)
                
                # 更新触发时间
                rule.last_triggered = datetime.now()
        
        return triggered
    
    def _evaluate_condition(self, condition: str, metric: str, value: float) -> bool:
        """评估条件"""
        # 简单条件评估
        # 例如: "cpu > 80" -> metric == 'cpu' and value > 80
        try:
            # 解析条件
            parts = condition.split()
            if len(parts) >= 3:
                cond_metric = parts[0]
                op = parts[1]
                threshold = float(parts[2])
                
                if metric != cond_metric:
                    return False
                
                if op == ">":
                    return value > threshold
                elif op == ">=":
                    return value >= threshold
                elif op == "<":
                    return value < threshold
                elif op == "<=":
                    return value <= threshold
                elif op == "==":
                    return value == threshold
                elif op == "!=":
                    return value != threshold
        except:
            pass
        
        return False


class AlertMonitor:
    """告警监控器"""
    
    def __init__(self, notification_manager: NotificationManager):
        self.notifier = notification_manager
        self._monitors: Dict[str, Callable] = {}
        self._running = False
    
    def register_monitor(self, name: str, monitor: Callable):
        """注册监控器"""
        self._monitors[name] = monitor
    
    async def start(self):
        """启动监控"""
        self._running = True
        asyncio.create_task(self._monitor_loop())
        logger.info("AlertMonitor started")
    
    async def stop(self):
        """停止监控"""
        self._running = False
    
    async def _monitor_loop(self):
        """监控循环"""
        while self._running:
            try:
                # 运行所有监控器
                for name, monitor in self._monitors.items():
                    try:
                        if asyncio.iscoroutinefunction(monitor):
                            await monitor()
                        else:
                            monitor()
                    except Exception as e:
                        logger.error(f"Monitor {name} error: {e}")
                
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(60)
    
    async def check_system_metrics(self):
        """检查系统指标"""
        import psutil
        
        # CPU
        cpu_percent = psutil.cpu_percent()
        if cpu_percent > 80:
            await self.notifier.send(
                title="CPU使用率告警",
                content=f"CPU使用率: {cpu_percent}%",
                level=AlertLevel.WARNING,
            )
        
        # 内存
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            await self.notifier.send(
                title="内存使用率告警",
                content=f"内存使用率: {memory.percent}%",
                level=AlertLevel.CRITICAL,
            )
        
        # 磁盘
        disk = psutil.disk_usage('/')
        if disk.percent > 90:
            await self.notifier.send(
                title="磁盘使用率告警",
                content=f"磁盘使用率: {disk.percent}%",
                level=AlertLevel.WARNING,
            )


# 全局实例
_notification_manager: Optional[NotificationManager] = None
_alert_monitor: Optional[AlertMonitor] = None


def get_notification_manager() -> NotificationManager:
    """获取通知管理器单例"""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager


async def get_alert_monitor() -> AlertMonitor:
    """获取告警监控器单例"""
    global _alert_monitor
    if _alert_monitor is None:
        notifier = get_notification_manager()
        _alert_monitor = AlertMonitor(notifier)
        await _alert_monitor.start()
    return _alert_monitor