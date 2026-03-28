"""
WanClaw 模块集成示例
展示如何使用各个模块构建完整应用
"""

import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_distributed_gateway():
    """分布式Gateway示例"""
    from wanclaw.backend.gateway import DistributedGateway, get_session_store
    
    # 创建Gateway
    gateway = DistributedGateway(
        redis_url="redis://localhost:6379",
        node_id="node-1",
        cluster_name="wanclaw",
    )
    await gateway.connect()
    
    # 获取会话存储
    session_store = await get_session_store()
    
    # 订阅消息
    async def handler(message):
        logger.info(f"Received: {message}")
    
    await gateway.subscribe("test_channel", handler)
    
    # 广播消息
    await gateway.broadcast("test_channel", {"type": "test", "data": "hello"})
    
    # 获取在线节点
    nodes = await gateway.get_nodes()
    logger.info(f"Online nodes: {list(nodes.keys())}")
    
    await gateway.close()
    logger.info("Distributed Gateway example completed")


async def example_task_queue():
    """任务队列示例"""
    from wanclaw.backend.tasks import TaskQueue, TaskExecutor, TaskPriority
    
    # 创建任务队列
    queue = TaskQueue(redis_url="redis://localhost:6379", queue_name="demo_tasks")
    await queue.connect()
    
    # 创建执行器
    executor = TaskExecutor(queue, worker_name="demo-worker")
    
    # 注册任务处理器
    @executor.register("process_file")
    async def process_file(payload):
        filename = payload.get("filename")
        logger.info(f"Processing {filename}")
        await asyncio.sleep(1)  # 模拟处理
        return {"status": "completed", "filename": filename}
    
    # 启动执行器
    await executor.start()
    
    # 入队任务
    task_id = await queue.enqueue(
        name="process_file",
        payload={"filename": "report.pdf"},
        priority=TaskPriority.NORMAL,
    )
    logger.info(f"Task enqueued: {task_id}")
    
    # 等待执行
    await asyncio.sleep(2)
    
    # 获取任务状态
    task = await queue.get_task_status(task_id)
    logger.info(f"Task status: {task.status if task else 'not found'}")
    
    await executor.stop()
    await queue.close()
    logger.info("Task Queue example completed")


async def example_react_agent():
    """ReAct Agent示例"""
    from wanclaw.backend.ai.react_agent import (
        ReActAgent, SkillTool, SearchTool, CalculatorTool, MemoryTool
    )
    
    # 模拟LLM客户端
    class MockLLM:
        async def chat(self, messages, **kwargs):
            # 简单模拟
            return {"text": "I'll help you with that."}
    
    llm = MockLLM()
    
    # 模拟技能管理器
    class MockSkillManager:
        async def execute(self, skill_name, params):
            return {"result": f"Executed {skill_name} with {params}"}
    
    skill_manager = MockSkillManager()
    
    # 模拟记忆管理器
    class MockMemory:
        def remember(self, content, category):
            logger.info(f"Remembered: {content[:50]}...")
        
        def recall(self, query):
            return [{"content": "Previous task about data"}]
    
    memory = MockMemory()
    
    # 创建Agent
    tools = [
        SkillTool(skill_manager),
        CalculatorTool(),
    ]
    
    agent = ReActAgent(llm, tools, memory, max_iterations=10)
    
    # 运行
    result = await agent.run("Calculate 15 * 23")
    
    logger.info(f"Agent result: {result['response']}")
    logger.info(f"Iterations: {result['iterations']}")
    logger.info("ReAct Agent example completed")


async def example_workflow():
    """工作流示例"""
    from wanclaw.backend.workflows import (
        WorkflowEngine, NodeType, Workflow, WorkflowNode, WorkflowEdge
    )
    
    # 创建引擎
    engine = WorkflowEngine()
    
    # 创建工作流
    workflow = await engine.create_workflow(
        name="订单处理流程",
        description="处理订单的自动化流程",
    )
    
    # 添加节点
    workflow.nodes = [
        WorkflowNode(
            node_id="start_1",
            name="开始",
            node_type=NodeType.START,
        ),
        WorkflowNode(
            node_id="task_1",
            name="验证订单",
            node_type=NodeType.TASK,
            config={"task_name": "validate_order"},
        ),
        WorkflowNode(
            node_id="condition_1",
            name="检查金额",
            node_type=NodeType.CONDITION,
            config={"condition": "${amount} > 100"},
        ),
        WorkflowNode(
            node_id="task_2",
            name="审核",
            node_type=NodeType.TASK,
            config={"task_name": "manual_review"},
        ),
        WorkflowNode(
            node_id="task_3",
            name="自动处理",
            node_type=NodeType.TASK,
            config={"task_name": "auto_process"},
        ),
        WorkflowNode(
            node_id="end_1",
            name="结束",
            node_type=NodeType.END,
        ),
    ]
    
    # 添加边
    workflow.edges = [
        WorkflowEdge(edge_id="e1", source="start_1", target="task_1"),
        WorkflowEdge(edge_id="e2", source="task_1", target="condition_1"),
        WorkflowEdge(edge_id="e3", source="condition_1", target="task_2", condition="true"),
        WorkflowEdge(edge_id="e4", source="condition_1", target="task_3", condition="false"),
        WorkflowEdge(edge_id="e5", source="task_2", target="end_1"),
        WorkflowEdge(edge_id="e6", source="task_3", target="end_1"),
    ]
    
    # 注册任务执行器
    class MockTaskExecutor:
        async def execute_now(self, task_name, params):
            logger.info(f"Executing task: {task_name}")
            return type('obj', (object,), {'result': f'{task_name} done', 'task_id': 'mock'})()
    
    from wanclaw.backend.workflows.engine import TaskExecutor as WFTE
    engine.register_executor(NodeType.TASK, WFTE(MockTaskExecutor()))
    
    # 执行工作流
    context = await engine.execute(
        workflow.workflow_id,
        input_variables={"amount": 150}
    )
    
    logger.info(f"Workflow execution: {context.status}")
    logger.info("Workflow example completed")


async def example_rbac():
    """RBAC示例"""
    from wanclaw.backend.auth import (
        AuthService, Permission, RoleManager, UserManager
    )
    
    # 创建认证服务
    auth_service = AuthService()
    await auth_service.initialize()
    
    # 创建用户
    user = await auth_service.user_manager.create_user(
        username="alice",
        email="alice@example.com",
        password="password123",
        full_name="Alice Wang",
        roles=["operator"],
    )
    logger.info(f"User created: {user.username}")
    
    # 登录
    logged_in = await auth_service.login("alice", "password123")
    logger.info(f"Login result: {'success' if logged_in else 'failed'}")
    
    # 检查权限
    has_perm = await auth_service.check_permission(
        user.user_id,
        Permission.SKILL_EXECUTE
    )
    logger.info(f"Has skill execute permission: {has_perm}")
    
    logger.info("RBAC example completed")


async def example_tenant():
    """多租户示例"""
    from wanclaw.backend.auth import (
        TenantService, PlanType, TenantStatus
    )
    
    # 创建租户服务
    tenant_service = TenantService()
    await tenant_service.initialize()
    
    # 创建租户
    result = await tenant_service.create_tenant_with_admin(
        tenant_name="厦门万岳科技",
        tenant_code="wanyue",
        admin_username="admin",
        admin_email="admin@wanyue.com",
        admin_password="wanclaw",
        plan=PlanType.PROFESSIONAL,
    )
    
    tenant = result["tenant"]
    admin = result["admin_user"]
    
    logger.info(f"Tenant created: {tenant.name}")
    logger.info(f"Admin created: {admin.username}")
    logger.info(f"Plan: {tenant.plan.value}")
    
    # 创建店铺
    store = await tenant_service.store_manager.create_store(
        tenant_id=tenant.tenant_id,
        name="天猫旗舰店",
        platform="taobao",
    )
    logger.info(f"Store created: {store.name if store else 'failed'}")
    
    # 创建客服
    agent = await tenant_service.agent_manager.create_agent(
        tenant_id=tenant.tenant_id,
        user_id="user_123",
        name="客服小王",
        role="operator",
    )
    logger.info(f"Agent created: {agent.name if agent else 'failed'}")
    
    logger.info("Tenant example completed")


async def example_notification():
    """告警通知示例"""
    from wanclaw.backend.notification import (
        get_notification_manager, ChannelType, AlertLevel
    )
    
    notifier = get_notification_manager()
    
    # 添加钉钉配置
    config = await notifier.add_config(
        name="钉钉告警",
        channel=ChannelType.DINGTALK,
        config_data={"webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx"},
        recipients=["13800138000"],
    )
    logger.info(f"Config added: {config.name}")
    
    # 发送通知
    results = await notifier.send(
        title="系统告警",
        content="CPU使用率达到85%",
        level=AlertLevel.WARNING,
    )
    logger.info(f"Notification sent: {len(results)} recipients")
    
    # 添加告警规则
    rule = await notifier.add_rule(
        name="CPU告警",
        condition="cpu > 80",
        level=AlertLevel.WARNING,
        channels=["dingtalk"],
        cooldown_seconds=300,
    )
    logger.info(f"Rule added: {rule.name}")
    
    logger.info("Notification example completed")


async def example_api_gateway():
    """API网关示例"""
    from wanclaw.backend.api_gateway import APIGateway, APIRoute
    
    # 创建网关
    gateway = APIGateway(redis_url="redis://localhost:6379")
    await gateway.initialize()
    
    # 定义处理函数
    async def handle_hello(api_key, query_params, body):
        return {
            "message": "Hello, World!",
            "user": api_key.name if api_key else "anonymous",
        }
    
    async def handle_status(api_key, query_params, body):
        return gateway.get_stats()
    
    # 注册路由
    gateway.register_route(APIRoute(
        path="/api/hello",
        method="GET",
        handler=handle_hello,
        auth_required=False,
    ))
    
    gateway.register_route(APIRoute(
        path="/api/status",
        method="GET",
        handler=handle_status,
        auth_required=True,
        permissions=["system:info"],
    ))
    
    # 模拟请求
    response = await gateway.handle_request(
        method="GET",
        path="/api/hello",
        headers={},
    )
    logger.info(f"Response: {response}")
    
    stats = await gateway.get_stats()
    logger.info(f"Gateway stats: {stats}")
    
    await gateway.close()
    logger.info("API Gateway example completed")


async def example_analytics():
    """数据分析示例"""
    from wanclaw.backend.analytics import get_analytics, get_revenue_analytics
    
    # 获取分析服务
    analytics = await get_analytics()
    revenue = await get_revenue_analytics()
    
    # 记录DAU
    await analytics.record_dau("user_001")
    await analytics.record_dau("user_002")
    await analytics.record_dau("user_003")
    
    # 获取DAU
    dau = await analytics.get_dau()
    logger.info(f"DAU: {dau}")
    
    # 记录收入
    await revenue.record_revenue(
        tenant_id="tenant_001",
        plan="professional",
        amount=299.0,
        payment_method="alipay",
    )
    
    # 获取收入统计
    mrr = await revenue.get_mrr()
    arr = await revenue.get_arr()
    logger.info(f"MRR: {mrr}, ARR: {arr}")
    
    logger.info("Analytics example completed")


async def example_audit():
    """审计示例"""
    from wanclaw.backend.audit import get_audit_service, AuditAction, AuditResource
    
    audit = await get_audit_service()
    
    # 记录审计日志
    await audit.logger.log(
        action=AuditAction.USER_LOGIN,
        resource_type=AuditResource.USER,
        resource_id="user_001",
        user_id="user_001",
        status="success",
        details={"ip": "192.168.1.1"},
        ip_address="192.168.1.1",
    )
    
    await audit.logger.log(
        action=AuditAction.SKILL_EXECUTE,
        resource_type=AuditResource.SKILL,
        resource_id="skill_pdf_process",
        user_id="user_001",
        status="success",
        details={"filename": "document.pdf"},
    )
    
    # 查询审计日志
    entries = await audit.query.query(
        user_id="user_001",
        limit=10,
    )
    logger.info(f"Audit entries: {len(entries)}")
    
    # 获取用户活动摘要
    activity = await audit.query.get_user_activity("user_001")
    logger.info(f"User activity: {activity['total_actions']} actions")
    
    logger.info("Audit example completed")


async def main():
    """运行所有示例"""
    logger.info("=" * 50)
    logger.info("WanClaw 模块集成示例")
    logger.info("=" * 50)
    
    examples = [
        ("RBAC", example_rbac),
        ("多租户", example_tenant),
        ("API网关", example_api_gateway),
        ("告警通知", example_notification),
        ("数据分析", example_analytics),
        ("审计", example_audit),
    ]
    
    for name, func in examples:
        try:
            logger.info(f"\n--- {name} ---")
            await func()
        except Exception as e:
            logger.error(f"{name} failed: {e}")
    
    logger.info("\n" + "=" * 50)
    logger.info("所有示例完成")
    logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
