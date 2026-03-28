"""
数据统计与营收分析
支持DAU/MAU、转化漏斗、收入报表、实时监控
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from enum import Enum
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    RATE = "rate"


@dataclass
class Metric:
    """指标"""
    metric_id: str
    name: str
    metric_type: MetricType
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Event:
    """事件"""
    event_id: str
    event_name: str
    user_id: str
    tenant_id: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ReportConfig:
    """报表配置"""
    report_id: str
    name: str
    report_type: str
    metrics: List[str] = field(default_factory=list)
    dimensions: List[str] = field(default_factory=list)
    filters: Dict[str, Any] = field(default_factory=dict)
    schedule: Optional[str] = None


@dataclass
class RevenueRecord:
    """收入记录"""
    record_id: str
    tenant_id: str
    plan: str
    amount: float
    currency: str = "CNY"
    payment_method: str = ""
    transaction_id: str = ""
    status: str = "completed"
    created_at: datetime = field(default_factory=datetime.now)


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def increment(self, name: str, value: float = 1, labels: Dict = None):
        """增加计数器"""
        labels = labels or {}
        
        key = f"metrics:{name}"
        if labels:
            label_str = ":".join(f"{k}={v}" for k, v in sorted(labels.items()))
            key = f"{key}:{label_str}"
        
        await self.redis.incrbyfloat(key, value)
        
        # 设置过期时间（默认1天）
        await self.redis.expire(key, 86400)
    
    async def gauge(self, name: str, value: float, labels: Dict = None):
        """设置仪表值"""
        labels = labels or {}
        
        key = f"metrics:{name}"
        if labels:
            label_str = ":".join(f"{k}={v}" for k, v in sorted(labels.items()))
            key = f"{key}:{label_str}"
        
        await self.redis.set(key, value)
    
    async def histogram(self, name: str, value: float, labels: Dict = None):
        """记录直方图"""
        labels = labels or {}
        
        key = f"metrics:{name}:histogram"
        if labels:
            label_str = ":".join(f"{k}={v}" for k, v in sorted(labels.items()))
            key = f"{key}:{label_str}"
        
        # 使用Redis Sorted Set存储分布
        await self.redis.zadd(key, {str(value): value})
        await self.redis.expire(key, 86400)
    
    async def get_value(self, name: str, labels: Dict = None) -> float:
        """获取指标值"""
        key = f"metrics:{name}"
        if labels:
            label_str = ":".join(f"{k}={v}" for k, v in sorted(labels.items()))
            key = f"{key}:{label_str}"
        
        value = await self.redis.get(key)
        return float(value) if value else 0


class EventTracker:
    """事件追踪器"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def track(
        self,
        event_name: str,
        user_id: str,
        tenant_id: str = None,
        properties: Dict = None,
    ):
        """追踪事件"""
        event = Event(
            event_id=f"evt_{uuid.uuid4().hex[:16]}",
            event_name=event_name,
            user_id=user_id,
            tenant_id=tenant_id,
            properties=properties or {},
        )
        
        # 存储事件
        date_str = datetime.now().strftime("%Y%m%d")
        key = f"events:{date_str}"
        
        await self.redis.lpush(key, json.dumps({
            "event_id": event.event_id,
            "event_name": event.event_name,
            "user_id": event.user_id,
            "tenant_id": event.tenant_id,
            "properties": event.properties,
            "timestamp": event.timestamp.isoformat(),
        }))
        
        # 修剪旧事件
        await self.redis.ltrim(key, 0, 10000)
        
        logger.debug(f"Event tracked: {event_name} by {user_id}")
    
    async def get_events(
        self,
        event_name: str = None,
        user_id: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100,
    ) -> List[Event]:
        """查询事件"""
        events = []
        pattern = "events:*"
        
        async for key in self.redis.scan_iter(match=pattern):
            async for evt_json in self.redis.lrange(key, 0, -1):
                evt = json.loads(evt_json)
                
                if event_name and evt.get("event_name") != event_name:
                    continue
                if user_id and evt.get("user_id") != user_id:
                    continue
                
                events.append(Event(
                    event_id=evt["event_id"],
                    event_name=evt["event_name"],
                    user_id=evt["user_id"],
                    tenant_id=evt.get("tenant_id"),
                    properties=evt.get("properties", {}),
                    timestamp=datetime.fromisoformat(evt["timestamp"]),
                ))
                
                if len(events) >= limit:
                    break
        
        return events[:limit]


class AnalyticsDashboard:
    """分析仪表盘"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.metrics = MetricsCollector(redis_client)
        self.events = EventTracker(redis_client)
    
    async def get_dau(self, date: date = None) -> int:
        """获取日活用户数(DAU)"""
        date = date or datetime.now().date()
        date_str = date.strftime("%Y%m%d")
        
        key = f"dau:{date_str}"
        value = await self.redis.scard(key)
        return value or 0
    
    async def record_dau(self, user_id: str, date: date = None):
        """记录日活用户"""
        date = date or datetime.now().date()
        date_str = date.strftime("%Y%m%d")
        
        key = f"dau:{date_str}"
        await self.redis.sadd(key, user_id)
        await self.redis.expire(key, 86400 * 7)  # 保留7天
    
    async def get_mau(self, year_month: str = None) -> int:
        """获取月活用户数(MAU)"""
        if not year_month:
            now = datetime.now()
            year_month = f"{now.year}{now.month:02d}"
        
        count = 0
        pattern = f"dau:*"
        
        async for key in self.redis.scan_iter(match=pattern):
            if year_month in key:
                count += await self.redis.scard(key)
        
        return count
    
    async def get_conversion_funnel(
        self,
        steps: List[str],
        start_date: date,
        end_date: date,
    ) -> List[Dict]:
        """获取转化漏斗"""
        results = []
        
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y%m%d")
            
            step_counts = []
            for step in steps:
                key = f"funnel:{date_str}:{step}"
                count = await self.redis.get(key)
                step_counts.append(int(count) if count else 0)
            
            results.append({
                "date": date_str,
                "steps": dict(zip(steps, step_counts)),
            })
            
            current_date += timedelta(days=1)
        
        return results
    
    async def record_funnel_step(
        self,
        step: str,
        user_id: str,
        date: date = None,
    ):
        """记录漏斗步骤"""
        date = date or datetime.now().date()
        date_str = date.strftime("%Y%m%d")
        
        key = f"funnel:{date_str}:{step}"
        await self.redis.sadd(key, user_id)
        await self.redis.expire(key, 86400 * 90)
    
    async def get_session_stats(self, tenant_id: str = None) -> Dict:
        """获取会话统计"""
        pattern = f"session:*"
        total_sessions = 0
        total_messages = 0
        avg_duration = 0
        durations = []
        
        async for key in self.redis.scan_iter(match=pattern):
            if tenant_id:
                # 需要从key中提取tenant_id
                pass
            
            session_data = await self.redis.hgetall(key)
            if session_data:
                total_sessions += 1
                total_messages += int(session_data.get("messages", 0))
                duration = int(session_data.get("duration", 0))
                if duration > 0:
                    durations.append(duration)
        
        if durations:
            avg_duration = sum(durations) / len(durations)
        
        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "avg_duration_seconds": avg_duration,
            "avg_messages_per_session": total_messages / total_sessions if total_sessions > 0 else 0,
        }


class RevenueAnalytics:
    """营收分析"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self._records: List[RevenueRecord] = []
    
    async def record_revenue(
        self,
        tenant_id: str,
        plan: str,
        amount: float,
        currency: str = "CNY",
        payment_method: str = "",
        transaction_id: str = "",
    ) -> RevenueRecord:
        """记录收入"""
        record = RevenueRecord(
            record_id=f"rev_{uuid.uuid4().hex[:16]}",
            tenant_id=tenant_id,
            plan=plan,
            amount=amount,
            currency=currency,
            payment_method=payment_method,
            transaction_id=transaction_id,
        )
        
        self._records.append(record)
        
        # 存储
        key = f"revenue:{datetime.now().strftime('%Y%m')}"
        await self.redis.lpush(key, json.dumps({
            "record_id": record.record_id,
            "tenant_id": record.tenant_id,
            "plan": record.plan,
            "amount": record.amount,
            "currency": record.currency,
            "payment_method": record.payment_method,
            "transaction_id": record.transaction_id,
            "created_at": record.created_at.isoformat(),
        }))
        
        # 更新汇总
        summary_key = f"revenue_summary:{datetime.now().strftime('%Y%m')}"
        await self.redis.hincrbyfloat(summary_key, plan, amount)
        
        return record
    
    async def get_revenue_by_period(
        self,
        start_date: date,
        end_date: date,
        group_by: str = "day",
    ) -> List[Dict]:
        """按时间段获取收入"""
        results = []
        
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y%m%d")
            month_str = current_date.strftime("%Y%m")
            
            if group_by == "day":
                key = f"revenue:{date_str}"
            else:
                key = f"revenue:{month_str}"
            
            records = await self.redis.lrange(key, 0, -1)
            
            total = 0
            for rec_json in records:
                rec = json.loads(rec_json)
                total += rec.get("amount", 0)
            
            results.append({
                "date": date_str,
                "revenue": total,
            })
            
            if group_by == "day":
                current_date += timedelta(days=1)
            else:
                # 跳到下个月
                if current_date.month == 12:
                    current_date = date(current_date.year + 1, 1, 1)
                else:
                    current_date = date(current_date.year, current_date.month + 1, 1)
        
        return results
    
    async def get_revenue_by_plan(self, year_month: str = None) -> Dict:
        """按套餐获取收入"""
        if not year_month:
            year_month = datetime.now().strftime("%Y%m")
        
        summary_key = f"revenue_summary:{year_month}"
        summary = await self.redis.hgetall(summary_key)
        
        return {plan: float(amount) for plan, amount in summary.items()}
    
    async def get_total_revenue(
        self,
        start_date: date = None,
        end_date: date = None,
    ) -> float:
        """获取总收入"""
        total = 0
        
        start = start_date or (datetime.now() - timedelta(days=30)).date()
        end = end_date or datetime.now().date()
        
        current = start
        while current <= end:
            key = f"revenue:{current.strftime('%Y%m%d')}"
            records = await self.redis.lrange(key, 0, -1)
            
            for rec_json in records:
                rec = json.loads(rec_json)
                total += rec.get("amount", 0)
            
            current += timedelta(days=1)
        
        return total
    
    async def get_mrr(self) -> float:
        """获取月度经常性收入(MRR)"""
        # MRR = 所有活跃订阅的平均月费
        current_month = datetime.now().strftime("%Y%m")
        summary_key = f"revenue_summary:{current_month}"
        summary = await self.redis.hgetall(summary_key)
        
        total = sum(float(amount) for amount in summary.values())
        return total
    
    async def get_arr(self) -> float:
        """获取年度经常性收入(ARR)"""
        mrr = await self.get_mrr()
        return mrr * 12
    
    async def get_arpu(self) -> float:
        """获取平均每用户收入(ARPU)"""
        # 需要获取用户数
        total_revenue = await self.get_total_revenue()
        
        # 估算用户数
        pattern = "dau:*"
        total_users = 0
        async for key in self.redis.scan_iter(match=pattern):
            total_users += await self.redis.scard(key)
        
        return total_revenue / total_users if total_users > 0 else 0


class ReportGenerator:
    """报表生成器"""
    
    def __init__(
        self,
        redis_client,
        dashboard: AnalyticsDashboard,
        revenue: RevenueAnalytics,
    ):
        self.redis = redis_client
        self.dashboard = dashboard
        self.revenue = revenue
    
    async def generate_daily_report(self, date: date = None) -> Dict:
        """生成日报"""
        date = date or datetime.now().date()
        
        # 用户统计
        dau = await self.dashboard.get_dau(date)
        
        # 会话统计
        session_stats = await self.dashboard.get_session_stats()
        
        # 收入
        revenue = await self.revenue.get_total_revenue(date, date)
        
        return {
            "date": date.strftime("%Y-%m-%d"),
            "users": {
                "dau": dau,
            },
            "sessions": session_stats,
            "revenue": revenue,
            "generated_at": datetime.now().isoformat(),
        }
    
    async def generate_weekly_report(self, start_date: date = None) -> Dict:
        """生成周报"""
        start = start_date or (datetime.now() - timedelta(days=7)).date()
        end = start + timedelta(days=6)
        
        daily_reports = []
        current = start
        while current <= end:
            report = await self.generate_daily_report(current)
            daily_reports.append(report)
            current += timedelta(days=1)
        
        # 汇总
        total_dau = sum(r["users"]["dau"] for r in daily_reports) // len(daily_reports)
        total_revenue = sum(r["revenue"] for r in daily_reports)
        
        return {
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
            "summary": {
                "avg_dau": total_dau,
                "total_revenue": total_revenue,
            },
            "daily": daily_reports,
            "generated_at": datetime.now().isoformat(),
        }
    
    async def generate_monthly_report(self, year_month: str = None) -> Dict:
        """生成月报"""
        if not year_month:
            year_month = datetime.now().strftime("%Y%m")
        
        year = int(year_month[:4])
        month = int(year_month[4:])
        start_date = date(year, month, 1)
        
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        # 获取MAU
        mau = await self.dashboard.get_mau(year_month)
        
        # 按套餐收入
        revenue_by_plan = await self.revenue.get_revenue_by_plan(year_month)
        
        # 月收入
        monthly_revenue = await self.revenue.get_total_revenue(start_date, end_date)
        
        return {
            "year_month": year_month,
            "users": {
                "mau": mau,
            },
            "revenue": {
                "total": monthly_revenue,
                "by_plan": revenue_by_plan,
                "mrr": monthly_revenue,
                "arr": monthly_revenue * 12,
            },
            "generated_at": datetime.now().isoformat(),
        }


class RealTimeMonitor:
    """实时监控"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def record_request(
        self,
        path: str,
        method: str,
        status_code: int,
        duration_ms: int,
        tenant_id: str = None,
    ):
        """记录请求"""
        now = datetime.now()
        minute_key = now.strftime("%Y%m%d%H%M")
        
        # 请求计数
        await self.redis.hincrby(f"rt:requests:{minute_key}", "total", 1)
        
        # 状态码分布
        await self.redis.hincrby(f"rt:status:{minute_key}", str(status_code), 1)
        
        # 响应时间
        await self.redis.zadd(f"rt:latency:{minute_key}", {str(duration_ms): duration_ms})
        
        # 租户分布
        if tenant_id:
            await self.redis.hincrby(f"rt:tenants:{minute_key}", tenant_id, 1)
        
        # 过期时间
        await self.redis.expire(f"rt:requests:{minute_key}", 7200)
        await self.redis.expire(f"rt:status:{minute_key}", 7200)
        await self.redis.expire(f"rt:latency:{minute_key}", 7200)
        await self.redis.expire(f"rt:tenants:{minute_key}", 7200)
    
    async def get_current_qps(self) -> float:
        """获取当前QPS"""
        now = datetime.now()
        minute_key = now.strftime("%Y%m%d%H%M")
        
        requests = await self.redis.hget(f"rt:requests:{minute_key}", "total")
        return float(requests or 0) / 60
    
    async def get_avg_latency(self) -> float:
        """获取平均延迟"""
        now = datetime.now()
        minute_key = now.strftime("%Y%m%d%H%M")
        
        latencies = await self.redis.zrange(f"rt:latency:{minute_key}", 0, -1)
        if not latencies:
            return 0
        
        total = sum(int(l) for l in latencies)
        return total / len(latencies)
    
    async def get_p99_latency(self) -> float:
        """获取P99延迟"""
        now = datetime.now()
        minute_key = now.strftime("%Y%m%d%H%M")
        
        latencies = await self.redis.zrange(f"rt:latency:{minute_key}", 0, -1, withscores=True)
        if not latencies:
            return 0
        
        idx = int(len(latencies) * 0.99)
        return latencies[idx][1] if idx < len(latencies) else latencies[-1][1]


# 全局实例
_analytics: Optional[AnalyticsDashboard] = None
_revenue: Optional[RevenueAnalytics] = None


async def get_analytics(redis_client=None) -> AnalyticsDashboard:
    """获取分析仪表盘"""
    global _analytics
    if _analytics is None:
        import redis.asyncio as aioredis
        redis = redis_client or await aioredis.from_url("redis://localhost:6379")
        _analytics = AnalyticsDashboard(redis)
    return _analytics


async def get_revenue_analytics(redis_client=None) -> RevenueAnalytics:
    """获取营收分析"""
    global _revenue
    if _revenue is None:
        import redis.asyncio as aioredis
        redis = redis_client or await aioredis.from_url("redis://localhost:6379")
        _revenue = RevenueAnalytics(redis)
    return _revenue