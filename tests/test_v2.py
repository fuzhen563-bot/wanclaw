#!/usr/bin/env python3
"""
WanClaw V2.0 功能测试脚本
验证所有新增模块的基本功能
"""

import asyncio
import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def add_pass(self, name: str):
        self.passed += 1
        print(f"  ✓ {name}")
    
    def add_fail(self, name: str, reason: str):
        self.failed += 1
        self.errors.append(f"✗ {name}: {reason}")
        print(f"  ✗ {name}: {reason}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*50}")
        print(f"测试结果: {self.passed}/{total} 通过")
        if self.errors:
            print(f"\n失败项:")
            for e in self.errors:
                print(f"  {e}")
        return self.failed == 0


def banner(title: str):
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}")


class TestRunner:
    def __init__(self):
        self.result = TestResult()
    
    async def run_all_tests(self):
        banner("WanClaw V2.0 功能测试")
        
        # 1. 基础模块导入测试
        await self.test_imports()
        
        # 2. 数据结构测试
        await self.test_data_structures()
        
        # 3. 任务队列测试
        await self.test_task_queue()
        
        # 4. ReAct Agent测试
        await self.test_react_agent()
        
        # 5. 工作流引擎测试
        await self.test_workflow_engine()
        
        # 6. RBAC权限测试
        await self.test_rbac()
        
        # 7. 多租户测试
        await self.test_tenant()
        
        # 8. 告警通知测试
        await self.test_notification()
        
        # 9. API网关测试
        await self.test_api_gateway()
        
        # 10. 数据分析测试
        await self.test_analytics()
        
        # 11. 审计系统测试
        await self.test_audit()
        
        # 12. 桌面自动化测试
        await self.test_automation()
        
        # 13. RPA测试
        await self.test_rpa()
        
        # 14. 安全沙箱测试
        await self.test_sandbox()
        
        # 15. 分布式Gateway测试
        await self.test_distributed_gateway()
        
        return self.result.summary()
    
    async def test_imports(self):
        banner("1. 模块导入测试")
        modules = [
            ("wanclaw.backend.gateway", "DistributedGateway"),
            ("wanclaw.backend.tasks", "TaskQueue"),
            ("wanclaw.backend.ai.react_agent", "ReActAgent"),
            ("wanclaw.backend.workflows", "WorkflowEngine"),
            ("wanclaw.backend.auth.rbac", "AuthService"),
            ("wanclaw.backend.auth.tenant", "TenantService"),
            ("wanclaw.backend.notification.manager", "NotificationManager"),
            ("wanclaw.backend.api_gateway.gateway", "APIGateway"),
            ("wanclaw.backend.analytics.analytics", "AnalyticsDashboard"),
            ("wanclaw.backend.audit.audit", "AuditService"),
            ("wanclaw.backend.automation", "InputController"),
            ("wanclaw.backend.rpa", "BrowserDriver"),
            ("wanclaw.backend.automation.sandbox", "AutomationSandbox"),
        ]
        
        for module_name, class_name in modules:
            try:
                module = __import__(module_name, fromlist=[class_name])
                cls = getattr(module, class_name)
                self.result.add_pass(f"{module_name}.{class_name}")
            except Exception as e:
                self.result.add_fail(f"{module_name}.{class_name}", str(e))
    
    async def test_data_structures(self):
        banner("2. 数据结构测试")
        
        # 测试 TaskQueue 数据结构
        try:
            from wanclaw.backend.tasks.tasks import Task, TaskStatus, TaskPriority
            
            task = Task(
                task_id="test-001",
                name="测试任务",
                payload={"key": "value"},
                priority=TaskPriority.HIGH,
            )
            assert task.task_id == "test-001"
            assert task.name == "测试任务"
            assert task.status == TaskStatus.PENDING
            assert task.priority == TaskPriority.HIGH
            self.result.add_pass("Task 数据结构")
        except Exception as e:
            self.result.add_fail("Task 数据结构", str(e))
        
        # 测试 Workflow 数据结构
        try:
            from wanclaw.backend.workflows import Workflow, WorkflowNode, NodeType
            
            node = WorkflowNode(
                node_id="node-1",
                name="测试节点",
                node_type=NodeType.TASK,
                config={"task_name": "test"},
            )
            assert node.node_id == "node-1"
            assert node.node_type == NodeType.TASK
            self.result.add_pass("WorkflowNode 数据结构")
        except Exception as e:
            self.result.add_fail("WorkflowNode 数据结构", str(e))
        
        # 测试 Permission 枚举
        try:
            from wanclaw.backend.auth import Permission
            assert Permission.USER_READ.value == "user:read"
            assert Permission.SKILL_EXECUTE.value == "skill:execute"
            self.result.add_pass("Permission 枚举")
        except Exception as e:
            self.result.add_fail("Permission 枚举", str(e))
        
        # 测试 PlanType 枚举
        try:
            from wanclaw.backend.auth import PlanType, TenantStatus
            assert PlanType.FREE.value == "free"
            assert TenantStatus.ACTIVE.value == "active"
            self.result.add_pass("PlanType/TenantStatus 枚举")
        except Exception as e:
            self.result.add_fail("PlanType/TenantStatus 枚举", str(e))
        
        # 测试 AlertLevel 枚举
        try:
            from wanclaw.backend.notification import AlertLevel, ChannelType
            assert AlertLevel.WARNING.value == "warning"
            assert ChannelType.DINGTALK.value == "dingtalk"
            self.result.add_pass("AlertLevel/ChannelType 枚举")
        except Exception as e:
            self.result.add_fail("AlertLevel/ChannelType 枚举", str(e))
    
    async def test_task_queue(self):
        banner("3. 任务队列测试")
        
        try:
            from wanclaw.backend.tasks.tasks import TaskQueue, TaskExecutor, TaskPriority, Task
            
            queue = TaskQueue(redis_url="redis://localhost:6379", queue_name="test_queue")
            
            # 测试任务创建
            task_id = "test-task-001"
            task_data = queue._task_to_dict(Task(
                task_id=task_id,
                name="测试任务",
                payload={"test": True},
                priority=TaskPriority.NORMAL,
            ))
            
            assert task_data["task_id"] == task_id
            assert task_data["name"] == "测试任务"
            assert task_data["status"] == "pending"
            
            # 测试任务状态转换
            from wanclaw.backend.tasks.tasks import TaskStatus
            assert TaskStatus.PENDING.value == "pending"
            assert TaskStatus.RUNNING.value == "running"
            assert TaskStatus.COMPLETED.value == "completed"
            assert TaskStatus.FAILED.value == "failed"
            
            self.result.add_pass("任务队列数据结构")
            self.result.add_pass("任务状态转换")
        except Exception as e:
            self.result.add_fail("任务队列测试", str(e))
        
        # 测试优先级队列
        try:
            from wanclaw.backend.tasks.tasks import TaskPriority
            assert TaskPriority.LOW.value == 0
            assert TaskPriority.URGENT.value == 20
            self.result.add_pass("任务优先级队列")
        except Exception as e:
            self.result.add_fail("任务优先级队列", str(e))
    
    async def test_react_agent(self):
        banner("4. ReAct Agent测试")
        
        try:
            from wanclaw.backend.ai.react_agent import (
                ReActAgent, SkillTool, SearchTool, CalculatorTool, 
                FileOperationTool, MemoryTool
            )
            
            # 测试工具注册
            class MockLLM:
                async def chat(self, messages, **kwargs):
                    return {"text": "测试响应"}
            
            class MockSkillManager:
                async def execute(self, skill_name, params=None):
                    return {"result": "skill_executed"}
            
            llm = MockLLM()
            skill_mgr = MockSkillManager()
            
            # 创建工具
            calc = CalculatorTool()
            skill_tool = SkillTool(skill_mgr)
            
            # 验证工具schema
            calc_schema = calc.get_schema()
            assert calc_schema["name"] == "calculator"
            assert "expression" in calc_schema["parameters"]["properties"]
            
            skill_schema = skill_tool.get_schema()
            assert skill_schema["name"] == "execute_skill"
            assert "skill_name" in skill_schema["parameters"]["required"]
            
            self.result.add_pass("ReAct 工具创建")
            self.result.add_pass("工具 Schema 验证")
            
            # 测试 Agent 创建
            agent = ReActAgent(llm, tools=[calc, skill_tool], max_iterations=5)
            assert agent.max_iterations == 5
            assert len(agent.tools) == 2
            
            self.result.add_pass("ReAct Agent 创建")
            
        except Exception as e:
            self.result.add_fail("ReAct Agent测试", str(e))
    
    async def test_workflow_engine(self):
        banner("5. 工作流引擎测试")
        
        try:
            from wanclaw.backend.workflows import (
                WorkflowEngine, Workflow, WorkflowNode, WorkflowEdge,
                NodeType, NodeStatus, TriggerType
            )
            
            # 创建工作流引擎
            engine = WorkflowEngine()
            
            # 创建工作流
            workflow = Workflow(
                workflow_id="wf-001",
                name="测试工作流",
                description="工作流测试",
                trigger=TriggerType.MANUAL,
            )
            
            assert workflow.workflow_id == "wf-001"
            assert workflow.name == "测试工作流"
            assert workflow.trigger == TriggerType.MANUAL
            
            # 添加节点
            start_node = WorkflowNode(
                node_id="start",
                name="开始",
                node_type=NodeType.START,
            )
            task_node = WorkflowNode(
                node_id="task1",
                name="执行任务",
                node_type=NodeType.TASK,
                config={"task_name": "test_task"},
            )
            end_node = WorkflowNode(
                node_id="end",
                name="结束",
                node_type=NodeType.END,
            )
            
            workflow.nodes = [start_node, task_node, end_node]
            
            # 添加边
            edge1 = WorkflowEdge(edge_id="e1", source="start", target="task1")
            edge2 = WorkflowEdge(edge_id="e2", source="task1", target="end")
            workflow.edges = [edge1, edge2]
            
            assert len(workflow.nodes) == 3
            assert len(workflow.edges) == 2
            
            # 测试DAG构建
            dag = engine._build_dag(workflow)
            assert "start" in dag
            assert "task1" in dag
            assert dag["start"] == ["task1"]
            
            self.result.add_pass("工作流创建")
            self.result.add_pass("工作流节点")
            self.result.add_pass("工作流边")
            self.result.add_pass("DAG构建")
            
        except Exception as e:
            self.result.add_fail("工作流引擎测试", str(e))
    
    async def test_rbac(self):
        banner("6. RBAC权限测试")
        
        try:
            from wanclaw.backend.auth.rbac import (
                AuthService, RoleManager, UserManager, PermissionChecker,
                Permission, Role, User
            )
            
            # 测试权限枚举
            assert Permission.USER_READ.value == "user:read"
            assert Permission.USER_CREATE.value == "user:create"
            assert Permission.SKILL_EXECUTE.value == "skill:execute"
            assert Permission.WORKFLOW_EXECUTE.value == "workflow:execute"
            
            # 测试角色创建
            role = Role(
                role_id="test-role",
                name="测试角色",
                description="用于测试的角色",
                permissions={Permission.USER_READ.value, Permission.SKILL_EXECUTE.value},
            )
            assert role.name == "测试角色"
            assert Permission.USER_READ.value in role.permissions
            
            # 测试用户创建
            user = User(
                user_id="user-001",
                username="testuser",
                email="test@example.com",
                full_name="测试用户",
                roles=["test-role"],
            )
            assert user.username == "testuser"
            assert user.is_active == True
            
            self.result.add_pass("权限枚举")
            self.result.add_pass("角色创建")
            self.result.add_pass("用户创建")
            
        except Exception as e:
            self.result.add_fail("RBAC测试", str(e))
    
    async def test_tenant(self):
        banner("7. 多租户测试")
        
        try:
            from wanclaw.backend.auth.tenant import (
                TenantService, TenantManager, StoreManager, AgentManager,
                Tenant, Store, Agent, Plan, PlanType, TenantStatus
            )
            
            # 测试套餐
            plan = Plan(
                plan_id="pro",
                name="专业版",
                plan_type=PlanType.PROFESSIONAL,
                price=299.0,
                max_users=50,
                max_stores=10,
                features=["AI", "RPA", "工作流"],
            )
            assert plan.name == "专业版"
            assert plan.price == 299.0
            assert plan.max_users == 50
            
            # 测试租户
            tenant = Tenant(
                tenant_id="tenant-001",
                name="测试公司",
                code="test",
                status=TenantStatus.ACTIVE,
                plan=PlanType.PROFESSIONAL,
            )
            assert tenant.name == "测试公司"
            assert tenant.status == TenantStatus.ACTIVE
            
            # 测试店铺
            store = Store(
                store_id="store-001",
                tenant_id="tenant-001",
                name="天猫店",
                platform="taobao",
            )
            assert store.name == "天猫店"
            assert store.platform == "taobao"
            
            # 测试客服
            agent = Agent(
                agent_id="agent-001",
                tenant_id="tenant-001",
                store_id="store-001",
                user_id="user-001",
                name="客服小王",
                role="operator",
            )
            assert agent.name == "客服小王"
            assert agent.role == "operator"
            
            self.result.add_pass("套餐创建")
            self.result.add_pass("租户创建")
            self.result.add_pass("店铺创建")
            self.result.add_pass("客服创建")
            
        except Exception as e:
            self.result.add_fail("多租户测试", str(e))
    
    async def test_notification(self):
        banner("8. 告警通知测试")
        
        try:
            from wanclaw.backend.notification.manager import (
                NotificationManager, Notification, NotificationConfig,
                AlertRule, AlertLevel, ChannelType
            )
            
            # 测试通知配置
            config = NotificationConfig(
                config_id="config-001",
                name="钉钉告警",
                channel=ChannelType.DINGTALK,
                config_data={"webhook": "https://example.com"},
                recipients=["13800138000"],
            )
            assert config.name == "钉钉告警"
            assert config.channel == ChannelType.DINGTALK
            
            # 测试告警规则
            rule = AlertRule(
                rule_id="rule-001",
                name="CPU告警",
                condition="cpu > 80",
                level=AlertLevel.WARNING,
                channels=["dingtalk"],
                cooldown_seconds=300,
            )
            assert rule.name == "CPU告警"
            assert rule.level == AlertLevel.WARNING
            
            # 测试通知管理器
            manager = NotificationManager()
            assert len(manager._channels) >= 5  # 默认至少5个渠道
            
            # 测试条件评估
            result = manager._evaluate_condition("cpu > 80", "cpu", 85)
            assert result == True
            
            result = manager._evaluate_condition("cpu > 80", "cpu", 70)
            assert result == False
            
            self.result.add_pass("通知配置")
            self.result.add_pass("告警规则")
            self.result.add_pass("通知管理器")
            self.result.add_pass("条件评估")
            
        except Exception as e:
            self.result.add_fail("告警通知测试", str(e))
    
    async def test_api_gateway(self):
        banner("9. API网关测试")
        
        try:
            from wanclaw.backend.api_gateway.gateway import (
                APIGateway, APIKey, APIRoute, RateLimiter,
                RequestLog, RateLimitType
            )
            
            # 测试API Key
            api_key = APIKey(
                key_id="ak-001",
                key_hash="abc123",
                name="测试Key",
                user_id="user-001",
                rate_limit=100,
            )
            assert api_key.name == "测试Key"
            assert api_key.is_active == True
            
            # 测试路由
            async def test_handler(api_key, query, body):
                return {"result": "ok"}
            
            route = APIRoute(
                path="/api/test",
                method="GET",
                handler=test_handler,
                auth_required=True,
                rate_limit=50,
            )
            assert route.path == "/api/test"
            assert route.auth_required == True
            
            self.result.add_pass("API Key创建")
            self.result.add_pass("API Route创建")
            
        except Exception as e:
            self.result.add_fail("API网关测试", str(e))
    
    async def test_analytics(self):
        banner("10. 数据分析测试")
        
        try:
            from wanclaw.backend.analytics.analytics import (
                AnalyticsDashboard, RevenueAnalytics, ReportGenerator,
                MetricType, Metric, Event
            )
            
            # 测试指标
            metric = Metric(
                metric_id="m-001",
                name="test_metric",
                metric_type=MetricType.COUNTER,
                value=100,
            )
            assert metric.name == "test_metric"
            assert metric.value == 100
            
            # 测试事件
            event = Event(
                event_id="evt-001",
                event_name="page_view",
                user_id="user-001",
                properties={"page": "/home"},
            )
            assert event.event_name == "page_view"
            assert event.properties["page"] == "/home"
            
            self.result.add_pass("指标创建")
            self.result.add_pass("事件创建")
            
        except Exception as e:
            self.result.add_fail("数据分析测试", str(e))
    
    async def test_audit(self):
        banner("11. 审计系统测试")
        
        try:
            from wanclaw.backend.audit.audit import (
                AuditService, AuditLogger, AuditEntry,
                AuditAction, AuditResource
            )
            
            # 测试审计动作
            assert AuditAction.USER_LOGIN.value == "user.login"
            assert AuditAction.SKILL_EXECUTE.value == "skill.execute"
            assert AuditAction.WORKFLOW_EXECUTE.value == "workflow.execute"
            
            # 测试审计资源
            assert AuditResource.USER.value == "user"
            assert AuditResource.TENANT.value == "tenant"
            assert AuditResource.SKILL.value == "skill"
            
            # 测试审计条目
            entry = AuditEntry(
                entry_id="audit-001",
                timestamp=datetime.now(),
                action=AuditAction.USER_LOGIN.value,
                resource_type=AuditResource.USER.value,
                resource_id="user-001",
                user_id="user-001",
                status="success",
                ip_address="192.168.1.1",
            )
            assert entry.action == "user.login"
            assert entry.status == "success"
            
            self.result.add_pass("审计动作枚举")
            self.result.add_pass("审计资源枚举")
            self.result.add_pass("审计条目创建")
            
        except Exception as e:
            self.result.add_fail("审计系统测试", str(e))
    
    async def test_automation(self):
        banner("12. 桌面自动化测试")
        
        try:
            from wanclaw.backend.automation import (
                InputController, Screenshot, VisionController,
                MouseButton, Point, Rectangle, WindowManager,
                WindowState, WindowInfo
            )
            
            # 测试鼠标按钮
            assert MouseButton.LEFT.value == "left"
            assert MouseButton.RIGHT.value == "right"
            
            # 测试坐标点
            point = Point(x=100, y=200)
            assert point.x == 100
            assert point.to_tuple() == (100, 200)
            
            # 测试矩形
            rect = Rectangle(x=0, y=0, width=1920, height=1080)
            assert rect.width == 1920
            assert rect.center == Point(x=960, y=540)
            
            # 测试 WindowState
            assert WindowState.NORMAL.value == "normal"
            assert WindowState.MINIMIZED.value == "minimized"
            assert WindowState.MAXIMIZED.value == "maximized"
            assert WindowState.FULLSCREEN.value == "fullscreen"
            assert WindowState.HIDDEN.value == "hidden"
            
            # 测试 WindowInfo
            info = WindowInfo(
                hwnd=12345,
                title="Test Window",
                process_name="test.exe",
                bounds=(0, 0, 800, 600),
                state=WindowState.NORMAL,
                is_active=True,
                pid=9999
            )
            assert info.title == "Test Window"
            assert info.state == WindowState.NORMAL
            assert info.is_active == True
            
            # 测试 WindowManager 创建（不依赖实际平台）
            wm = WindowManager()
            assert hasattr(wm, 'enumerate_windows')
            assert hasattr(wm, 'activate')
            assert hasattr(wm, 'minimize')
            assert hasattr(wm, 'maximize')
            assert hasattr(wm, 'restore')
            assert hasattr(wm, 'close')
            assert hasattr(wm, 'hide')
            assert hasattr(wm, 'move_resize')
            assert hasattr(wm, 'center')
            assert hasattr(wm, 'get_active')
            assert hasattr(wm, 'find_by_title')
            assert hasattr(wm, 'find_by_process')
            assert hasattr(wm, 'screenshot_window')
            
            self.result.add_pass("鼠标按钮枚举")
            self.result.add_pass("坐标点计算")
            self.result.add_pass("矩形计算")
            self.result.add_pass("WindowState枚举")
            self.result.add_pass("WindowInfo创建")
            self.result.add_pass("WindowManager统一接口")
            
        except Exception as e:
            self.result.add_fail("桌面自动化测试", str(e))
    
    async def test_rpa(self):
        banner("13. RPA测试")
        
        try:
            from wanclaw.backend.rpa import (
                BrowserDriver, BrowserPool, RPAManager,
                BrowserType, ElementLocator, ElementLocatorType
            )
            
            # 测试浏览器类型
            assert BrowserType.CHROMIUM.value == "chromium"
            assert BrowserType.FIREFOX.value == "firefox"
            
            # 测试元素定位器
            locator = ElementLocator(
                type=ElementLocatorType.ID,
                value="username",
            )
            assert locator.type == ElementLocatorType.ID
            assert locator.value == "username"
            
            self.result.add_pass("浏览器类型枚举")
            self.result.add_pass("元素定位器创建")
            
        except Exception as e:
            self.result.add_fail("RPA测试", str(e))
    
    async def test_sandbox(self):
        banner("14. 安全沙箱测试")
        
        try:
            from wanclaw.backend.automation.sandbox import (
                AutomationSandbox, CodeValidator, InputSanitizer,
                SecurityLevel, RateLimiter
            )
            
            # 测试安全级别
            assert SecurityLevel.NONE.value == "none"
            assert SecurityLevel.BASIC.value == "basic"
            assert SecurityLevel.STRICT.value == "strict"
            
            # 测试代码验证器
            validator = CodeValidator(SecurityLevel.BASIC)
            
            # 测试安全代码
            safe_code = "print('hello')"
            result = validator.validate(safe_code)
            assert result.success == True
            
            # 测试危险代码检测
            dangerous_code = "import os; os.system('rm -rf /')"
            result = validator.validate(dangerous_code)
            assert result.success == False
            
            # 测试输入净化
            sanitizer = InputSanitizer()
            clean = sanitizer.sanitize("hello; drop table users")
            assert ";" not in clean or "drop" not in clean.lower()
            
            self.result.add_pass("安全级别枚举")
            self.result.add_pass("代码验证器")
            self.result.add_pass("危险代码检测")
            self.result.add_pass("输入净化")
            
        except Exception as e:
            self.result.add_fail("安全沙箱测试", str(e))
    
    async def test_distributed_gateway(self):
        banner("15. 分布式Gateway测试")
        
        try:
            from wanclaw.backend.gateway.distributed import (
                DistributedGateway, SessionStore, MessageQueue,
                MessagePriority, GatewayNode, SessionState
            )
            
            # 测试消息优先级
            assert MessagePriority.HIGH.value == "high"
            assert MessagePriority.NORMAL.value == "normal"
            
            # 测试节点
            node = GatewayNode(
                node_id="node-001",
                host="localhost",
                port=8000,
                status="online",
            )
            assert node.node_id == "node-001"
            assert node.status == "online"
            
            # 测试会话状态
            session = SessionState(
                session_id="sess-001",
                user_id="user-001",
                platform="web",
                data={"key": "value"},
            )
            assert session.session_id == "sess-001"
            assert session.data["key"] == "value"
            
            self.result.add_pass("消息优先级枚举")
            self.result.add_pass("网关节点创建")
            self.result.add_pass("会话状态创建")
            
        except Exception as e:
            self.result.add_fail("分布式Gateway测试", str(e))


async def main():
    print("""
    ╔═══════════════════════════════════════════════════╗
    ║                                                   ║
    ║          WanClaw V2.0 功能测试                     ║
    ║                                                   ║
    ╚═══════════════════════════════════════════════════╝
    """)
    
    runner = TestRunner()
    success = await runner.run_all_tests()
    
    print(f"\n测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if success:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查上述错误")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
