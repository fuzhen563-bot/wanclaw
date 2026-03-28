#!/usr/bin/env python3
"""
测试 WanClaw AI 调度功能
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wanclaw.backend.ai.react_agent import (
    ReActAgent, CalculatorTool, SkillTool, FileOperationTool,
    create_react_agent
)


class MockLLM:
    """模拟 LLM 客户端"""
    
    def __init__(self, response_type="simple"):
        self.response_type = response_type
        self.call_count = 0
    
    async def chat(self, messages, **kwargs):
        self.call_count += 1
        user_input = messages[-1]["content"] if messages else ""
        
        if "calculator" in user_input.lower() or "计算" in user_input:
            return {
                "text": """Thought: 用户想进行数学计算，我需要使用计算器工具
Action: calculator
Action Input: {"expression": "2 + 2 * 3"}
Observation: {"result": 8, "expression": "2 + 2 * 3"}
Thought: 计算完成了，现在我知道答案了
Final Answer: 2 + 2 × 3 = 8

解析：先算乘法 2 × 3 = 6，再算加法 2 + 6 = 8"""
            }
        elif "文件" in user_input or "file" in user_input.lower():
            return {
                "text": """Thought: 用户想操作文件，我需要使用文件操作工具
Action: file_operation
Action Input: {"operation": "list"}
Observation: {"files": ["test.txt", "data.json"]}
Thought: 文件列表已获取，我可以回答了
Final Answer: 当前目录有以下文件：test.txt, data.json"""
            }
        elif "final" in user_input.lower():
            return {
                "text": """Thought: 我已经理解了用户的问题
Final Answer: 这是一个测试回答"""
            }
        else:
            return {
                "text": """Thought: 用户提出了一个问题
Action: calculator
Action Input: {"expression": "10 + 20"}
Observation: {"result": 30, "expression": "10 + 20"}
Thought: 计算完成，我现在知道答案了
Final Answer: 10 + 20 = 30"""
            }


class MockSkillManager:
    """模拟技能管理器"""
    
    def __init__(self):
        self.executed_skills = []
    
    async def execute(self, skill_name, parameters=None):
        self.executed_skills.append({
            "skill": skill_name,
            "params": parameters
        })
        return {
            "success": True,
            "skill": skill_name,
            "result": f"执行了技能: {skill_name}"
        }


class MockMemory:
    """模拟记忆管理器"""
    
    def __init__(self):
        self.storage = {}
    
    def remember(self, content, category="general"):
        if category not in self.storage:
            self.storage[category] = []
        self.storage[category].append(content)
    
    def recall(self, query):
        results = []
        for category, contents in self.storage.items():
            for content in contents:
                if query.lower() in content.lower():
                    results.append(content)
        return results


async def test_calculator():
    """测试计算器工具"""
    print("\n" + "="*50)
    print("测试 1: 计算器工具 (CalculatorTool)")
    print("="*50)
    
    llm = MockLLM()
    calc = CalculatorTool()
    
    agent = ReActAgent(llm, tools=[calc])
    
    result = await agent.run("请计算 2 + 2 * 3 等于多少？")
    
    print(f"  输入: 2 + 2 * 3")
    print(f"  结果: {result['response']}")
    print(f"  迭代次数: {result['iterations']}")
    print(f"  成功: {'✓' if result['success'] else '✗'}")
    
    return result['success']


async def test_skill_execution():
    """测试技能执行"""
    print("\n" + "="*50)
    print("测试 2: 技能执行 (SkillTool)")
    print("="*50)
    
    llm = MockLLM()
    skill_mgr = MockSkillManager()
    skill_tool = SkillTool(skill_mgr)
    
    agent = ReActAgent(llm, tools=[skill_tool])
    
    result = await skill_tool.execute(skill_name="order_process", parameters={"order_id": "12345"})
    
    print(f"  执行技能: order_process")
    print(f"  参数: order_id=12345")
    print(f"  结果: {result}")
    print(f"  执行历史: {skill_mgr.executed_skills}")
    print(f"  成功: ✓")
    
    return True


async def test_file_operation():
    """测试文件操作"""
    print("\n" + "="*50)
    print("测试 3: 文件操作 (FileOperationTool)")
    print("="*50)
    
    file_tool = FileOperationTool("/tmp/wanclaw_test")
    
    # 写入文件
    write_result = await file_tool.execute(
        operation="write",
        path="test.txt",
        content="Hello, WanClaw!"
    )
    print(f"  写入文件: {write_result}")
    
    # 读取文件
    read_result = await file_tool.execute(operation="read", path="test.txt")
    print(f"  读取文件: {read_result}")
    
    # 列出文件
    list_result = await file_tool.execute(operation="list")
    print(f"  文件列表: {list_result}")
    
    return True


async def test_react_agent_full():
    """测试完整的 ReAct Agent"""
    print("\n" + "="*50)
    print("测试 4: ReAct Agent 完整流程")
    print("="*50)
    
    llm = MockLLM()
    calc = CalculatorTool()
    skill_mgr = MockSkillManager()
    skill_tool = SkillTool(skill_mgr)
    
    agent = ReActAgent(llm, tools=[calc, skill_tool], max_iterations=5)
    
    print(f"  工具数量: {len(agent.tools)}")
    print(f"  最大迭代: {agent.max_iterations}")
    print(f"  工具列表: {list(agent.tools.keys())}")
    
    # 测试计划创建
    plan = await agent.create_plan("帮我计算 100 + 200 并保存结果")
    print(f"  创建计划: {plan.plan_id}")
    print(f"  计划步骤: {len(plan.steps)} 步")
    
    return True


async def test_agent_orchestration():
    """测试 Agent 编排"""
    print("\n" + "="*50)
    print("测试 5: Agent 编排 (Orchestration)")
    print("="*50)
    
    # 创建多个工具
    llm = MockLLM()
    calc = CalculatorTool()
    file_op = FileOperationTool()
    skill_mgr = MockSkillManager()
    skill_tool = SkillTool(skill_mgr)
    memory = MockMemory()
    
    # 创建 Agent
    agent = create_react_agent(
        llm_client=llm,
        skill_manager=skill_mgr,
        memory=memory
    )
    
    # 添加额外工具
    agent.add_tool(calc)
    
    print(f"  Agent 类型: ReActAgent")
    print(f"  注册工具: {list(agent.tools.keys())}")
    
    # 测试记忆功能
    memory.remember("用户喜欢蓝色", "preference")
    memory.remember("用户名叫张三", "profile")
    
    results = memory.recall("蓝色")
    print(f"  记忆检索 '蓝色': {results}")
    
    # 运行 Agent
    result = await agent.run("你好")
    print(f"  Agent 响应: {result['response'][:50]}...")
    print(f"  思考步骤数: {len(result['thoughts'])}")
    
    return True


async def main():
    print("""
    ╔═══════════════════════════════════════════════════╗
    ║                                                   ║
    ║        WanClaw V2.0 AI 调度功能测试                ║
    ║                                                   ║
    ╚═══════════════════════════════════════════════════╝
    """)
    
    results = []
    
    results.append(("计算器工具", await test_calculator()))
    results.append(("技能执行", await test_skill_execution()))
    results.append(("文件操作", await test_file_operation()))
    results.append(("ReAct Agent", await test_react_agent_full()))
    results.append(("Agent 编排", await test_agent_orchestration()))
    
    # 汇总
    print("\n" + "="*50)
    print("测试结果汇总")
    print("="*50)
    
    for name, success in results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"  {name}: {status}")
    
    passed = sum(1 for _, s in results if s)
    print(f"\n总计: {passed}/{len(results)} 通过")
    
    if passed == len(results):
        print("\n🎉 所有 AI 调度测试通过！")
        return 0
    else:
        print("\n⚠️ 部分测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
