"""
BackupManagerSkill - WanClaw 官方技能插件
自动生成的插件适配器
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def run(**kwargs) -> Dict[str, Any]:
    """
    插件入口函数
    桥接到内置技能类
    """
    try:
        from wanclaw.backend.skills import BaseSkill, SkillResult, get_skill_manager

        manager = get_skill_manager()
        skill_instance = manager.get_skill("BackupManagerSkill")

        if not skill_instance:
            return {
                "success": False,
                "error": "Skill not found: BackupManagerSkill",
                "message": "内置技能未注册"
            }

        result = await skill_instance.execute(kwargs)

        return {
            "success": result.success,
            "message": result.message,
            "data": result.data,
            "error": result.error,
            "execution_time": result.execution_time,
        }
    except ImportError as e:
        logger.error(f"Failed to import skill system: {e}")
        return {
            "success": False,
            "error": f"Import error: {str(e)}",
            "message": "无法加载技能系统"
        }
    except Exception as e:
        logger.error(f"Skill execution failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "技能执行失败"
        }
