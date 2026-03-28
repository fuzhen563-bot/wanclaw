import os
import json
import sys
import importlib.util
import logging
import traceback
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any

logger = logging.getLogger(__name__)

DEFAULT_MANAGED_DIR = "~/.wanclaw/skills"
DEFAULT_BUNDLED_DIR = None
DEFAULT_WORKSPACE_DIR = "~/.wanclaw"

SKILL_MD_NAMES = {"SKILL.md", "skill.md", "Skill.md"}
PLUGIN_JSON_NAME = "plugin.json"
MAIN_PY_NAME = "main.py"

SOURCE_PRIORITY = {
    "extra": 0,
    "bundled": 1,
    "managed": 2,
    "workspace": 3,
}


@dataclass
class LoadedSkill:
    name: str
    format: str
    description: str
    file_path: str
    base_dir: str
    enabled: bool = True
    metadata: Optional[Any] = None
    user_invocable: bool = True
    manifest: Optional[Dict] = None
    module_path: Optional[str] = None
    tools: List[Any] = field(default_factory=list)
    _skill_def: Optional[Any] = None
    _source: str = "unknown"
    _mtime: float = 0.0

    def __post_init__(self):
        if not isinstance(self.tools, list):
            self.tools = list(self.tools)


class SkillLoader:
    def __init__(
        self,
        managed_dir: str = DEFAULT_MANAGED_DIR,
        bundled_dir: Optional[str] = DEFAULT_BUNDLED_DIR,
        workspace_dir: str = DEFAULT_WORKSPACE_DIR,
        extra_dirs: Optional[List[str]] = None,
        plugin_manager=None,
    ):
        self.managed_dir = os.path.expanduser(managed_dir)
        self.bundled_dir = os.path.expanduser(bundled_dir) if bundled_dir else None
        self.workspace_dir = os.path.expanduser(workspace_dir)
        self.extra_dirs = [os.path.expanduser(d) for d in (extra_dirs or [])]
        self.plugin_manager = plugin_manager

    def discover_all(self) -> List[LoadedSkill]:
        skills: List[LoadedSkill] = []
        sources = [
            ("extra", d) for d in self.extra_dirs
        ]
        if self.bundled_dir:
            sources.append(("bundled", self.bundled_dir))
        sources.append(("managed", self.managed_dir))
        sources.append(("workspace", self.workspace_dir))

        for source_name, base_dir in sources:
            if os.path.isdir(base_dir):
                found = self.discover_from_dir(base_dir, source_name)
                skills.extend(found)

        return self._deduplicate_skills(skills)

    def discover_from_dir(self, base_dir: str, source: str) -> List[LoadedSkill]:
        skills: List[LoadedSkill] = []
        skill_dirs: Dict[str, Dict[str, str]] = {}

        for dirpath, dirnames, filenames in os.walk(base_dir):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]

            for filename in filenames:
                if filename in SKILL_MD_NAMES:
                    skill_dir = dirpath
                    if skill_dir not in skill_dirs:
                        skill_dirs[skill_dir] = {}
                    skill_dirs[skill_dir]["sk_md"] = os.path.join(dirpath, filename)
                elif filename == PLUGIN_JSON_NAME:
                    skill_dir = dirpath
                    if skill_dir not in skill_dirs:
                        skill_dirs[skill_dir] = {}
                    skill_dirs[skill_dir]["plugin_json"] = os.path.join(dirpath, filename)

        for skill_dir, files in skill_dirs.items():
            loaded: Optional[LoadedSkill] = None
            if "sk_md" in files:
                loaded = self._load_skill_md(skill_dir, files["sk_md"], source)
            elif "plugin_json" in files:
                loaded = self._load_plugin_json(skill_dir, files["plugin_json"], source)

            if loaded:
                skills.append(loaded)

        return skills

    def _load_skill_md(self, skill_dir: str, sk_md_path: str, source: str) -> Optional[LoadedSkill]:
        try:
            content = Path(sk_md_path).read_text()
        except Exception as e:
            logger.warning(f"Failed to read {sk_md_path}: {e}")
            return None

        try:
            from wanclaw.backend.agent.skill_md import SkillMarkdownParser
            parser = SkillMarkdownParser()
            skill_def = parser.parse(content, sk_md_path)
        except Exception as e:
            logger.warning(f"Failed to parse SKILL.md {sk_md_path}: {e}")
            return None

        mtime = 0.0
        try:
            mtime = os.path.getmtime(sk_md_path)
        except Exception:
            pass

        metadata = skill_def.get("wanclaw")
        requires_tools = skill_def.get("requires", {}).get("bins", [])

        tools = self._build_tools_from_skill_md(
            skill_def.get("name", "unnamed"),
            skill_def.get("description", ""),
            skill_def.get("body", ""),
            requires_tools,
        )

        return LoadedSkill(
            name=skill_def.get("name", "unnamed"),
            format="sk_md",
            description=skill_def.get("description", ""),
            file_path=sk_md_path,
            base_dir=skill_dir,
            enabled=True,
            metadata=metadata,
            user_invocable=skill_def.get("user-invocable", True),
            tools=tools,
            _skill_def=skill_def,
            _source=source,
            _mtime=mtime,
        )

    def _load_plugin_json(self, skill_dir: str, plugin_json_path: str, source: str) -> Optional[LoadedSkill]:
        try:
            manifest = json.loads(Path(plugin_json_path).read_text())
        except Exception as e:
            logger.warning(f"Failed to read {plugin_json_path}: {e}")
            return None

        name = manifest.get("name", os.path.basename(skill_dir))
        main_py_path = os.path.join(skill_dir, MAIN_PY_NAME)
        if not os.path.exists(main_py_path):
            logger.debug(f"plugin.json found but no main.py in {skill_dir}")
            return None

        mtime = 0.0
        try:
            mtime = os.path.getmtime(main_py_path)
        except Exception:
            pass

        tools = self._load_python_skill(skill_dir, manifest, source)
        if tools is None:
            tools = []

        return LoadedSkill(
            name=name,
            format="plugin_json",
            description=manifest.get("description", ""),
            file_path=plugin_json_path,
            base_dir=skill_dir,
            enabled=manifest.get("enabled", True),
            manifest=manifest,
            module_path=main_py_path,
            tools=tools,
            _source=source,
            _mtime=mtime,
        )

    def _load_python_skill(
        self, skill_dir: str, manifest: Dict, source: str
    ) -> Optional[List[Any]]:
        main_py_path = os.path.join(skill_dir, MAIN_PY_NAME)
        plugin_name = manifest.get("name", os.path.basename(skill_dir))
        tools: List[Any] = []

        class _StubPluginApi:
            def __init__(self, plugin_mgr):
                self._name = plugin_name
                self._config = manifest.get("config", {})
                self._tools: Dict[str, Any] = {}
                self._plugin_manager = plugin_mgr
                self._mgr = self

            def set_plugin_name(self, name: str):
                self._name = name

            def set_config(self, config: Dict):
                self._config = config

            def log(self, level: str, msg: str):
                getattr(logger, level.lower(), logger.info)(
                    f"[plugin:{self._name}] {msg}"
                )

            def register_tool(
                self,
                name: str,
                description: str,
                parameters: Dict,
                handler: Callable,
                requires_confirm: bool = False,
            ):
                from wanclaw.backend.agent.core import Tool
                tool = Tool(
                    name=f"{self._name}_{name}" if self._name else name,
                    description=description,
                    parameters=parameters,
                    handler=handler,
                    requires_confirm=requires_confirm,
                )
                self._tools[tool.name] = tool
                tools.append(tool)

            def register_hook(self, event: str, handler: Callable, priority: int = 100, blocking: bool = False):
                if self._plugin_manager:
                    self._plugin_manager.register_plugin_hook(
                        self._name, event, handler, priority, blocking
                    )

            def register_gateway_hook(self, command: str, handler: Callable, priority: int = 100):
                if self._plugin_manager:
                    self._plugin_manager.register_plugin_gateway_hook(
                        self._name, command, handler, priority
                    )

            def register_skill(self, name: str, description: str, handler: Callable, tags: Optional[List[str]] = None):
                pass

            def get_config(self, key: str, default: Any = None) -> Any:
                return self._config.get(key, default)

            def get_workspace_path(self) -> str:
                return skill_dir

        api = _StubPluginApi(self.plugin_manager)
        api.set_plugin_name(plugin_name)

        try:
            spec = importlib.util.spec_from_file_location(
                f"wanclaw_skill_{plugin_name}", main_py_path
            )
            if spec is None or spec.loader is None:
                logger.warning(f"Failed to load spec for {main_py_path}")
                return tools

            module = importlib.util.module_from_spec(spec)
            module_name = f"wanclaw_skill_{plugin_name}"
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            if hasattr(module, "register"):
                module.register(api)
                logger.info(f"Plugin skill '{plugin_name}' loaded, {len(tools)} tools registered")
            else:
                logger.debug(f"Plugin skill '{plugin_name}' has no register() function")

        except Exception as e:
            logger.warning(f"Failed to load plugin skill '{plugin_name}' from {main_py_path}: {e}\n{traceback.format_exc()}")
            return None

        return tools

    def _build_tools_from_skill_md(
        self, name: str, description: str, body: str, requires_tools: List[str]
    ) -> List[Any]:
        from wanclaw.backend.agent.core import Tool
        tools: List[Any] = []

        if not requires_tools:
            requires_tools = ["bash"]

        def make_handler(tool_name: str):
            async def handler(params: Dict) -> str:
                return f"Skill '{name}' executed via {tool_name}. Implement skill body execution here."
            return handler

        for tool_name in requires_tools[:3]:
            tool = Tool(
                name=f"skill_{name}_{tool_name}",
                description=f"[{name}] {description} (via {tool_name})",
                parameters={"skill_body": "string"},
                handler=make_handler(tool_name),
            )
            tools.append(tool)

        return tools

    def _deduplicate_skills(self, skills: List[LoadedSkill]) -> List[LoadedSkill]:
        best: Dict[str, LoadedSkill] = {}
        for skill in skills:
            existing = best.get(skill.name)
            if existing is None:
                best[skill.name] = skill
            else:
                existing_priority = SOURCE_PRIORITY.get(existing._source, -1)
                new_priority = SOURCE_PRIORITY.get(skill._source, -1)
                if new_priority > existing_priority:
                    best[skill.name] = skill
        return list(best.values())

    def get_tools_for_skill(self, skill: LoadedSkill) -> List[Any]:
        return list(skill.tools)


class SkillManager:
    def __init__(
        self,
        loader: Optional[SkillLoader] = None,
        plugin_manager=None,
    ):
        self.loader = loader or SkillLoader(plugin_manager=plugin_manager)
        self.plugin_manager = plugin_manager
        self._skills: Dict[str, LoadedSkill] = {}

    def load_all(self) -> Dict[str, LoadedSkill]:
        skills = self.loader.discover_all()
        for skill in skills:
            self._skills[skill.name] = skill
        return self._skills

    def get_skill(self, name: str) -> Optional[LoadedSkill]:
        return self._skills.get(name)

    def get_tools(self) -> List[Any]:
        tools: List[Any] = []
        for skill in self._skills.values():
            if skill.enabled:
                tools.extend(self.loader.get_tools_for_skill(skill))
        if self.plugin_manager:
            tools.extend(self.plugin_manager.get_all_tools().values())
        return tools

    def is_skill_available(self, name: str) -> bool:
        skill = self._skills.get(name)
        if not skill or not skill.enabled:
            return False
        ok, _ = self.check_requires(skill)
        return ok

    def check_requires(self, skill: LoadedSkill) -> tuple[bool, List[str]]:
        missing: List[str] = []
        metadata = skill.metadata

        if skill.format == "sk_md" and metadata is not None:
            requires = getattr(metadata, "requires", None)
            if requires:
                for env_var in getattr(requires, "env", []):
                    if not os.environ.get(env_var):
                        missing.append(f"env:{env_var}")

                for bin_name in getattr(requires, "bins", []):
                    if not self._which(bin_name):
                        missing.append(f"bin:{bin_name}")

                for cfg_key in getattr(requires, "config", []):
                    pass

        elif skill.format == "plugin_json" and skill.manifest:
            deps = skill.manifest.get("dependencies", [])
            for dep in deps:
                if isinstance(dep, str):
                    if not self._which(dep):
                        missing.append(f"bin:{dep}")

        return (len(missing) == 0, missing)

    def _which(self, name: str) -> bool:
        if os.path.isabs(name) and os.path.exists(name):
            return True
        for dir_path in os.environ.get("PATH", "").split(os.pathsep):
            full = os.path.join(dir_path, name)
            if os.path.isfile(full) and os.access(full, os.X_OK):
                return True
        return False
