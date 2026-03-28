"""
WanClaw Skill System
技能系统，提供各种自动化能力
"""

import logging
from typing import Dict, List, Optional, Any, Callable, Type, Tuple
from abc import ABC, abstractmethod
from enum import Enum
import os
import sys
import importlib.util
import inspect

from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class SkillCategory(str, Enum):
    """技能分类"""
    OFFICE = "office"          # 办公自动化
    OPS = "ops"               # 运维管理
    BUSINESS = "business"     # 业务支持
    SECURITY = "security"     # 安全管理
    MARKETING = "marketing"   # 营销获客
    AI = "ai"                 # AI增强
    MANAGEMENT = "management" # 管理运营
    CUSTOM = "custom"         # 自定义技能


class SkillLevel(str, Enum):
    """技能难度级别"""
    BEGINNER = "beginner"     # 初级
    INTERMEDIATE = "intermediate"  # 中级
    ADVANCED = "advanced"     # 高级


class SkillResult(BaseModel):
    """技能执行结果"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="结果消息")
    data: Optional[Dict[str, Any]] = Field(None, description="返回数据")
    error: Optional[str] = Field(None, description="错误信息")
    execution_time: float = Field(0.0, description="执行时间（秒）")


class BaseSkill(ABC):
    """技能基类"""
    
    def __init__(self):
        self.name = self.__class__.__name__
        self.description = "基础技能"
        self.category = SkillCategory.CUSTOM
        self.level = SkillLevel.BEGINNER
        self.version = "1.0.0"
        self.author = "WanClaw Team"
        self.required_params: List[str] = []
        self.optional_params: Dict[str, Any] = {}
    
    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        """
        执行技能
        
        Args:
            params: 技能参数
            
        Returns:
            执行结果
        """
        pass
    
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        验证参数
        
        Args:
            params: 技能参数
            
        Returns:
            Tuple[是否有效, 错误信息]
        """
        # 检查必需参数
        for required_param in self.required_params:
            if required_param not in params:
                return False, f"缺少必需参数: {required_param}"
        
        # 检查参数类型（简单验证）
        for param_name, param_value in params.items():
            if param_name in self.optional_params:
                expected_type = self.optional_params[param_name]
                if not isinstance(param_value, expected_type):
                    return False, f"参数 {param_name} 类型错误，期望 {expected_type.__name__}"
        
        return True, None
    
    def get_info(self) -> Dict[str, Any]:
        """获取技能信息"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "level": self.level.value,
            "version": self.version,
            "author": self.author,
            "required_params": self.required_params,
            "optional_params": {k: v.__name__ for k, v in self.optional_params.items()}
        }


class DynamicSkill(BaseSkill):
    """动态加载的技能，适配 run() 函数"""
    
    def __init__(self, name: str, description: str, category: str, version: str, run_func):
        super().__init__()
        self.name = name
        self.description = description
        self.category = SkillCategory(category) if category in [e.value for e in SkillCategory] else SkillCategory.CUSTOM
        self.version = version
        self.author = "Community"
        self._run_func = run_func
    
    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        try:
            if inspect.iscoroutinefunction(self._run_func):
                result = await self._run_func(**params)
            else:
                result = self._run_func(**params)
            if isinstance(result, dict):
                return SkillResult(success=True, message=result.get("result", str(result)), data=result)
            return SkillResult(success=True, message=str(result))
        except Exception as e:
            return SkillResult(success=False, message=str(e), error=str(e))


class SkillManager:
    """技能管理器"""
    
    def __init__(self):
        self.skills: Dict[str, BaseSkill] = {}
        self.skill_registry: Dict[str, Type[BaseSkill]] = {}
        
        # 自动注册内置技能
        self._register_builtin_skills()
        # 加载已安装的技能
        self.load_installed_skills()
        # 加载官方插件
        self.load_official_plugins()
    
    def _register_builtin_skills(self):
        """注册内置技能"""
        try:
            # 办公自动化技能
            from wanclaw.backend.skills.office.file_manager import FileManagerSkill
            from wanclaw.backend.skills.office.email_processor import EmailProcessorSkill
            from wanclaw.backend.skills.office.spreadsheet_handler import SpreadsheetHandlerSkill
            from wanclaw.backend.skills.office.excel_processor import ExcelProcessorSkill
            from wanclaw.backend.skills.office.pdf_processor import PDFProcessorSkill
            from wanclaw.backend.skills.office.word_processor import WordProcessorSkill
            from wanclaw.backend.skills.office.batch_file_processor import BatchFileProcessorSkill
            from wanclaw.backend.skills.office.email_automation import EmailAutomationSkill
            from wanclaw.backend.skills.office.contract_extractor import ContractExtractorSkill

            self.register_skill(FileManagerSkill)
            self.register_skill(EmailProcessorSkill)
            self.register_skill(SpreadsheetHandlerSkill)
            self.register_skill(ExcelProcessorSkill)
            self.register_skill(PDFProcessorSkill)
            self.register_skill(WordProcessorSkill)
            self.register_skill(BatchFileProcessorSkill)
            self.register_skill(EmailAutomationSkill)
            self.register_skill(ContractExtractorSkill)

            # 运维技能
            from wanclaw.backend.skills.ops.process_monitor import ProcessMonitorSkill
            from wanclaw.backend.skills.ops.log_viewer import LogViewerSkill
            from wanclaw.backend.skills.ops.backup import BackupSkill
            from wanclaw.backend.skills.ops.health_checker import HealthCheckerSkill
            from wanclaw.backend.skills.ops.log_cleaner import LogCleanerSkill
            from wanclaw.backend.skills.ops.backup_manager import BackupManagerSkill

            self.register_skill(ProcessMonitorSkill)
            self.register_skill(LogViewerSkill)
            self.register_skill(BackupSkill)
            self.register_skill(HealthCheckerSkill)
            self.register_skill(LogCleanerSkill)
            self.register_skill(BackupManagerSkill)

            # 营销/客服技能
            from wanclaw.backend.skills.marketing.wechat_group_monitor import WeChatGroupMonitorSkill
            from wanclaw.backend.skills.marketing.media_processor import MediaProcessorSkill
            from wanclaw.backend.skills.marketing.customer_importer import CustomerImporterSkill
            from wanclaw.backend.skills.marketing.competitor_monitor import CompetitorMonitorSkill

            self.register_skill(WeChatGroupMonitorSkill)
            self.register_skill(MediaProcessorSkill)
            self.register_skill(CustomerImporterSkill)
            self.register_skill(CompetitorMonitorSkill)

            # 管理/运营技能
            from wanclaw.backend.skills.management.attendance_processor import AttendanceProcessorSkill
            from wanclaw.backend.skills.management.inventory_manager import InventoryManagerSkill
            from wanclaw.backend.skills.management.order_sync import OrderSyncSkill
            from wanclaw.backend.skills.management.meeting_notes_generator import MeetingNotesGeneratorSkill

            self.register_skill(AttendanceProcessorSkill)
            self.register_skill(InventoryManagerSkill)
            self.register_skill(OrderSyncSkill)
            self.register_skill(MeetingNotesGeneratorSkill)

            # 安全技能
            from wanclaw.backend.skills.security.security_scanner import SecurityScannerSkill

            self.register_skill(SecurityScannerSkill)

            # AI增强技能
            from wanclaw.backend.skills.ai.nlp_task_generator import NLPTaskGeneratorSkill
            from wanclaw.backend.skills.ai.copywriter_ai import CopywriterAISkill
            from wanclaw.backend.skills.ai.ocr_processor import OCRProcessorSkill
            from wanclaw.backend.skills.ai.workflow_chain import WorkflowChainSkill

            try:
                from wanclaw.backend.skills.ai.lancedb_memory import LanceDBMemorySkill
                self.register_skill(LanceDBMemorySkill)
                logger.info("LanceDBMemory 技能注册成功")
            except ImportError as e:
                logger.warning(f"LanceDBMemory 技能未注册 (lancedb未安装): {e}")

            self.register_skill(NLPTaskGeneratorSkill)
            self.register_skill(CopywriterAISkill)
            self.register_skill(OCRProcessorSkill)
            self.register_skill(WorkflowChainSkill)

            logger.info("内置技能注册完成")
        except ImportError as e:
            logger.warning(f"内置技能导入失败: {e}")
    
    def load_installed_skills(self):
        base = os.path.join(os.path.dirname(__file__), "installed")
        if not os.path.isdir(base):
            return
        for name in os.listdir(base):
            skill_dir = os.path.join(base, name)
            main_py = os.path.join(skill_dir, "main.py")
            if not os.path.isdir(skill_dir) or not os.path.exists(main_py):
                continue
            try:
                mod_name = f"wanclaw.backend.skills.installed.{name}"
                spec = importlib.util.spec_from_file_location(mod_name, main_py)
                if not spec or not spec.loader:
                    continue
                mod = importlib.util.module_from_spec(spec)
                sys.modules[mod_name] = mod
                spec.loader.exec_module(mod)
                run_func = getattr(mod, "run", None) or getattr(mod, "execute", None)
                if not run_func:
                    continue
                manifest_path = os.path.join(skill_dir, "manifest.json")
                info = {}
                if os.path.exists(manifest_path):
                    import json
                    with open(manifest_path) as f:
                        info = json.load(f)
                if name.lower() in self.skills:
                    continue
                skill = DynamicSkill(
                    name=name,
                    description=info.get("description", ""),
                    category=info.get("category", "custom"),
                    version=info.get("version", "1.0.0"),
                    run_func=run_func,
                )
                self.skills[name.lower()] = skill
                logger.info(f"动态加载技能: {name}")
            except Exception as e:
                logger.warning(f"加载技能 {name} 失败: {e}")
    
    def load_official_plugins(self):
        """加载官方插件（plugins/official 目录）"""
        # wanclaw/backend/skills/__init__.py -> wanclaw/ -> wanclaw/plugins/official
        base = os.path.join(os.path.dirname(__file__), "..", "..", "plugins", "official")
        if not os.path.isdir(base):
            logger.info("Official plugins directory not found, skipping")
            return
        
        for name in os.listdir(base):
            plugin_dir = os.path.join(base, name)
            main_py = os.path.join(plugin_dir, "main.py")
            manifest_path = os.path.join(plugin_dir, "manifest.json")
            plugin_json_path = os.path.join(plugin_dir, "plugin.json")
            
            if not os.path.isdir(plugin_dir) or not os.path.exists(main_py):
                continue
            
            try:
                mod_name = f"wanclaw.plugins.official.{name}"
                spec = importlib.util.spec_from_file_location(mod_name, main_py)
                if not spec or not spec.loader:
                    continue
                mod = importlib.util.module_from_spec(spec)
                sys.modules[mod_name] = mod
                spec.loader.exec_module(mod)
                run_func = getattr(mod, "run", None) or getattr(mod, "execute", None)
                if not run_func:
                    continue
                
                info = {"name": name, "description": "", "version": "2.0.0"}
                
                # 优先读取 plugin.json（ClawHub格式，优先使用）
                if os.path.exists(plugin_json_path):
                    import json
                    with open(plugin_json_path) as f:
                        pj = json.load(f)
                    info["name"] = pj.get("plugin_name", name)
                    info["description"] = pj.get("description", "")
                    info["version"] = pj.get("version", "2.0.0")
                    info["category"] = pj.get("category", "custom")
                # manifest.json 作为备用
                if os.path.exists(manifest_path):
                    import json
                    with open(manifest_path) as f:
                        manifest = json.load(f)
                    for k, v in manifest.items():
                        info.setdefault(k, v)
                
                skill = DynamicSkill(
                    name=info.get("name", name),
                    description=info.get("description", ""),
                    category=info.get("category", "custom"),
                    version=info.get("version", "2.0.0"),
                    run_func=run_func,
                )
                self.skills[name.lower()] = skill
                logger.info(f"官方插件加载: {name} ({info.get('description', '')[:30]}...)")
            except Exception as e:
                logger.warning(f"加载官方插件 {name} 失败: {e}")
    
    def register_skill(self, skill_class: Type[BaseSkill]):
        """
        注册技能类
        
        Args:
            skill_class: 技能类
        """
        skill_instance = skill_class()
        skill_name = skill_instance.name.lower()
        
        if skill_name in self.skills:
            logger.warning(f"技能已存在: {skill_name}")
            return
        
        self.skills[skill_name] = skill_instance
        self.skill_registry[skill_name] = skill_class
        
        logger.info(f"注册技能: {skill_name} ({skill_instance.description})")
    
    def unregister_skill(self, skill_name: str) -> bool:
        """
        注销技能
        
        Args:
            skill_name: 技能名称
            
        Returns:
            是否注销成功
        """
        if skill_name.lower() not in self.skills:
            logger.warning(f"技能不存在: {skill_name}")
            return False
        
        del self.skills[skill_name.lower()]
        del self.skill_registry[skill_name.lower()]
        
        logger.info(f"注销技能: {skill_name}")
        return True
    
    def get_skill(self, skill_name: str) -> Optional[BaseSkill]:
        """
        获取技能实例
        
        Args:
            skill_name: 技能名称
            
        Returns:
            技能实例
        """
        return self.skills.get(skill_name.lower())
    
    def list_skills(self, category: Optional[SkillCategory] = None) -> List[Dict[str, Any]]:
        """
        列出所有技能
        
        Args:
            category: 技能分类过滤
            
        Returns:
            技能信息列表
        """
        skills_info = []
        
        for skill in self.skills.values():
            if category and skill.category != category:
                continue
            
            skills_info.append(skill.get_info())
        
        return skills_info
    
    async def execute_skill(self, skill_name: str, params: Dict[str, Any]) -> SkillResult:
        """
        执行技能
        
        Args:
            skill_name: 技能名称
            params: 技能参数
            
        Returns:
            执行结果
        """
        import time
        start_time = time.time()
        
        skill = self.get_skill(skill_name)
        if not skill:
            return SkillResult(
                success=False,
                message=f"技能不存在: {skill_name}",
                error="Skill not found",
                data=None,
                execution_time=time.time() - start_time
            )
        
        # 验证参数
        is_valid, error_msg = skill.validate_params(params)
        if not is_valid:
            return SkillResult(
                success=False,
                message=error_msg,
                error="Invalid parameters",
                data=None,
                execution_time=time.time() - start_time
            )
        
        try:
            # 执行技能
            result = await skill.execute(params)
            
            # 确保结果包含执行时间
            if hasattr(result, 'execution_time'):
                result.execution_time = time.time() - start_time
                return result
            else:
                # 如果技能没有设置execution_time，创建一个新结果
                message_value = result.message if hasattr(result, 'message') and result.message is not None else "未知结果"
                return SkillResult(
                    success=result.success if hasattr(result, 'success') else False,
                    message=message_value,
                    data=result.data if hasattr(result, 'data') else None,
                    error=result.error if hasattr(result, 'error') else None,
                    execution_time=time.time() - start_time
                )
            
        except Exception as e:
            logger.error(f"技能执行异常: {skill_name} - {e}")
            return SkillResult(
                success=False,
                message=f"技能执行失败: {str(e)}",
                error=str(e),
                data=None,
                execution_time=time.time() - start_time
            )


# 全局技能管理器实例
_skill_manager: Optional[SkillManager] = None


def get_skill_manager() -> SkillManager:
    """获取全局技能管理器实例"""
    global _skill_manager
    if _skill_manager is None:
        _skill_manager = SkillManager()
    return _skill_manager