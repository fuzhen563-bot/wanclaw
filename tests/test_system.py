#!/usr/bin/env python3
"""
WanClaw 系统测试脚本
直接测试系统功能，避免相对导入问题
"""

import sys
import os
import asyncio
import logging

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "wanclaw"))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_skill_system():
    """测试技能系统"""
    try:
        from wanclaw.backend.skills import SkillManager, BaseSkill, SkillResult
        
        print("✅ 技能模块导入成功")
        
        # 使用全局技能管理器
        skill_manager = SkillManager()
        
        # 技能管理器会自动注册内置技能
        
        print(f"✅ 注册了 {len(skill_manager.skills)} 个技能:")
        for name in skill_manager.skills:
            print(f"   - {name}")
        
        # 测试列出技能
        print("\n📋 测试技能列表:")
        skills_list = skill_manager.list_skills()
        print(f"   技能数量: {len(skills_list)}")
        for skill_info in skills_list:
            print(f"   - {skill_info.get('name')}: {skill_info.get('description')}")
        
        # 测试执行list命令（通过list_skill技能）
        if "list_skill" in skill_manager.skills or "list" in skill_manager.skills:
            skill_name = "list_skill" if "list_skill" in skill_manager.skills else "list"
            list_result = await skill_manager.execute_skill(skill_name, {})
            print(f"   执行结果: {list_result.success}")
            if list_result.success and list_result.data:
                print(f"   数据: {list_result.data}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 技能系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_config_loading():
    """测试配置加载"""
    try:
        # 直接从main.py导入配置加载逻辑
        import yaml
        from pathlib import Path
        
        config_path = Path("/data/wanclaw/wanclaw/backend/im_adapter/config/config.yaml")
        
        if not config_path.exists():
            print(f"⚠️  配置文件不存在: {config_path}")
            return False
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        print(f"✅ 配置加载成功")
        print(f"   企业微信启用: {config.get('wecom', {}).get('enabled', False)}")
        print(f"   飞书启用: {config.get('feishu', {}).get('enabled', False)}")
        print(f"   QQ启用: {config.get('qq', {}).get('enabled', False)}")
        print(f"   微信启用: {config.get('wechat', {}).get('enabled', False)}")
        print(f"   Telegram启用: {config.get('telegram', {}).get('enabled', False)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 配置加载失败: {e}")
        return False

async def test_adapters_creation():
    """测试适配器创建"""
    try:
        print("📋 测试适配器导入:")
        
        adapter_classes = []
        test_config = {"enabled": True}
        
        # 测试每个适配器
        platforms = [
            ("wecom", "WeComAdapter"),
            ("feishu", "FeishuAdapter"),
            ("qq", "QQAdapter"),
            ("wechat", "WeChatAdapter"),
            ("telegram", "TelegramAdapter"),
        ]
        
        for platform, class_name in platforms:
            try:
                module = __import__(f"wanclaw.backend.im_adapter.adapters.{platform}", fromlist=[class_name])
                adapter_class = getattr(module, class_name)
                adapter_classes.append((platform, adapter_class))
                print(f"   ✅ {class_name} 导入成功")
            except ImportError as e:
                print(f"   ⚠️  {class_name} 导入失败: {e}")
            except Exception as e:
                print(f"   ⚠️  {class_name} 错误: {e}")
        
        print(f"\n📋 测试适配器实例化:")
        adapters_created = 0
        
        for platform, adapter_class in adapter_classes:
            try:
                adapter = adapter_class(test_config)
                adapters_created += 1
                print(f"   ✅ {adapter_class.__name__} 实例创建成功")
            except Exception as e:
                print(f"   ⚠️  {adapter_class.__name__} 实例创建失败: {e}")
        
        print(f"\n✅ 适配器测试完成: 导入 {len(adapter_classes)} 个适配器类, 成功创建 {adapters_created} 个实例")
        
        # 如果至少有一个适配器可用，测试就算通过
        return adapters_created > 0
        
    except Exception as e:
        logger.error(f"❌ 适配器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    print("🚀 WanClaw 系统测试开始")
    print("=" * 50)
    
    tests = [
        ("配置加载", test_config_loading),
        ("技能系统", test_skill_system),
        ("适配器创建", test_adapters_creation),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 测试: {test_name}")
        try:
            success = await test_func()
            results.append((test_name, success))
            if success:
                print(f"✅ {test_name} 测试通过")
            else:
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            logger.error(f"❌ {test_name} 测试异常: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"   {test_name}: {status}")
    
    print(f"\n📈 通过率: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 所有测试通过!")
        return 0
    else:
        print("⚠️  部分测试失败，请检查错误信息")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)