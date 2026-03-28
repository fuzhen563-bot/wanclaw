"""
WanClaw 单元测试
"""

import asyncio
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTaskQueue:
    """任务队列测试"""
    
    @pytest.mark.asyncio
    async def test_task_creation(self):
        """测试任务创建"""
        from wanclaw.backend.tasks import Task, TaskStatus, TaskPriority
        
        task = Task(
            task_id="test-001",
            name="test_task",
            payload={"key": "value"},
            priority=TaskPriority.NORMAL,
        )
        
        assert task.task_id == "test-001"
        assert task.name == "test_task"
        assert task.status == TaskStatus.PENDING
        assert task.payload["key"] == "value"
    
    @pytest.mark.asyncio
    async def test_task_priority(self):
        """测试任务优先级"""
        from wanclaw.backend.tasks import TaskPriority
        
        assert TaskPriority.LOW.value == 0
        assert TaskPriority.NORMAL.value == 5
        assert TaskPriority.HIGH.value == 10
        assert TaskPriority.URGENT.value == 20


class TestReActAgent:
    """ReAct Agent测试"""
    
    def test_tool_schema(self):
        """测试工具Schema"""
        from wanclaw.backend.ai.react_agent import CalculatorTool
        
        calc = CalculatorTool()
        schema = calc.get_schema()
        
        assert schema["name"] == "calculator"
        assert "expression" in schema["parameters"]["properties"]
    
    def test_skill_tool_schema(self):
        """测试技能工具Schema"""
        from wanclaw.backend.ai.react_agent import SkillTool
        
        class MockSkillManager:
            async def execute(self, name, params):
                return {"result": "ok"}
        
        skill = SkillTool(MockSkillManager())
        schema = skill.get_schema()
        
        assert schema["name"] == "execute_skill"
        assert "skill_name" in schema["parameters"]["required"]


class TestWorkflow:
    """工作流测试"""
    
    def test_node_types(self):
        """测试节点类型"""
        from wanclaw.backend.workflows import NodeType
        
        assert NodeType.START.value == "start"
        assert NodeType.END.value == "end"
        assert NodeType.TASK.value == "task"
        assert NodeType.CONDITION.value == "condition"
    
    def test_trigger_types(self):
        """测试触发类型"""
        from wanclaw.backend.workflows import TriggerType
        
        assert TriggerType.MANUAL.value == "manual"
        assert TriggerType.SCHEDULED.value == "scheduled"
        assert TriggerType.EVENT.value == "event"


class TestRBAC:
    """RBAC测试"""
    
    def test_permission_enum(self):
        """测试权限枚举"""
        from wanclaw.backend.auth import Permission
        
        assert Permission.USER_READ.value == "user:read"
        assert Permission.SKILL_EXECUTE.value == "skill:execute"
        assert Permission.CONFIG_UPDATE.value == "config:update"
    
    def test_permission_values(self):
        """测试权限值"""
        from wanclaw.backend.auth import Permission
        
        perms = [
            Permission.USER_READ,
            Permission.USER_CREATE,
            Permission.USER_UPDATE,
            Permission.USER_DELETE,
        ]
        
        assert len(perms) == 4


class TestTenant:
    """多租户测试"""
    
    def test_plan_types(self):
        """测试套餐类型"""
        from wanclaw.backend.auth import PlanType
        
        assert PlanType.FREE.value == "free"
        assert PlanType.BASIC.value == "basic"
        assert PlanType.PROFESSIONAL.value == "professional"
        assert PlanType.ENTERPRISE.value == "enterprise"
    
    def test_tenant_status(self):
        """测试租户状态"""
        from wanclaw.backend.auth import TenantStatus
        
        assert TenantStatus.ACTIVE.value == "active"
        assert TenantStatus.SUSPENDED.value == "suspended"
        assert TenantStatus.EXPIRED.value == "expired"


class TestNotification:
    """通知测试"""
    
    def test_channel_types(self):
        """测试渠道类型"""
        from wanclaw.backend.notification import ChannelType
        
        assert ChannelType.DINGTALK.value == "dingtalk"
        assert ChannelType.FEISHU.value == "feishu"
        assert ChannelType.EMAIL.value == "email"
        assert ChannelType.WEBHOOK.value == "webhook"
    
    def test_alert_levels(self):
        """测试告警级别"""
        from wanclaw.backend.notification import AlertLevel
        
        assert AlertLevel.INFO.value == "info"
        assert AlertLevel.WARNING.value == "warning"
        assert AlertLevel.ERROR.value == "error"
        assert AlertLevel.CRITICAL.value == "critical"


class TestAPIGateway:
    """API网关测试"""
    
    def test_rate_limit_types(self):
        """测试限流类型"""
        from wanclaw.backend.api_gateway import RateLimitType
        
        assert RateLimitType.PER_USER.value == "per_user"
        assert RateLimitType.PER_API_KEY.value == "per_api_key"
        assert RateLimitType.GLOBAL.value == "global"


class TestAnalytics:
    """数据分析测试"""
    
    def test_metric_types(self):
        """测试指标类型"""
        from wanclaw.backend.analytics import MetricType
        
        assert MetricType.COUNTER.value == "counter"
        assert MetricType.GAUGE.value == "gauge"
        assert MetricType.HISTOGRAM.value == "histogram"
        assert MetricType.RATE.value == "rate"


class TestAudit:
    """审计测试"""
    
    def test_audit_actions(self):
        """测试审计动作"""
        from wanclaw.backend.audit import AuditAction
        
        assert AuditAction.USER_LOGIN.value == "user.login"
        assert AuditAction.USER_LOGOUT.value == "user.logout"
        assert AuditAction.SKILL_EXECUTE.value == "skill.execute"
    
    def test_audit_resources(self):
        """测试审计资源"""
        from wanclaw.backend.audit import AuditResource
        
        assert AuditResource.USER.value == "user"
        assert AuditResource.TENANT.value == "tenant"
        assert AuditResource.SKILL.value == "skill"
        assert AuditResource.WORKFLOW.value == "workflow"


class TestAutomation:
    """自动化测试"""
    
    def test_mouse_buttons(self):
        """测试鼠标按钮"""
        from wanclaw.backend.automation import MouseButton
        
        assert MouseButton.LEFT.value == "left"
        assert MouseButton.RIGHT.value == "right"
        assert MouseButton.MIDDLE.value == "middle"
    
    def test_window_manager(self):
        """测试窗口管理器"""
        from wanclaw.backend.automation import WindowManager, WindowState, WindowInfo
        
        assert WindowState.NORMAL.value == "normal"
        assert WindowState.MINIMIZED.value == "minimized"
        assert WindowState.MAXIMIZED.value == "maximized"
        assert WindowState.FULLSCREEN.value == "fullscreen"
        assert WindowState.HIDDEN.value == "hidden"
        
        info = WindowInfo(
            hwnd=12345,
            title="Test",
            process_name="test.exe",
            bounds=(0, 0, 800, 600),
            state=WindowState.NORMAL,
            is_active=True,
            pid=9999
        )
        assert info.title == "Test"
        assert info.state == WindowState.NORMAL
        
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
    
    def test_browser_types(self):
        """测试浏览器类型"""
        from wanclaw.backend.rpa import BrowserType
        
        assert BrowserType.CHROMIUM.value == "chromium"
        assert BrowserType.FIREFOX.value == "firefox"
        assert BrowserType.WEBKIT.value == "webkit"
    
    def test_element_locator_types(self):
        """测试元素定位器类型"""
        from wanclaw.backend.rpa import ElementLocatorType
        
        assert ElementLocatorType.ID.value == "id"
        assert ElementLocatorType.CSS.value == "css"
        assert ElementLocatorType.XPATH.value == "xpath"
        assert ElementLocatorType.TEXT.value == "text"


class TestSandbox:
    """沙箱测试"""
    
    def test_security_levels(self):
        """测试安全级别"""
        from wanclaw.backend.automation.sandbox import SecurityLevel
        
        assert SecurityLevel.NONE.value == "none"
        assert SecurityLevel.BASIC.value == "basic"
        assert SecurityLevel.STRICT.value == "strict"
        assert SecurityLevel.SANDBOX.value == "sandbox"
    
    def test_code_validator_blocked_imports(self):
        """测试代码验证器的阻塞导入"""
        from wanclaw.backend.automation.sandbox import CodeValidator, SecurityLevel
        
        validator = CodeValidator(SecurityLevel.BASIC)
        
        assert "os" in validator.BLOCKED_IMPORTS
        assert "subprocess" in validator.BLOCKED_IMPORTS
        assert "requests" in validator.BLOCKED_IMPORTS


def run_tests():
    """运行所有测试"""
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    run_tests()
