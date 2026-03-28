import logging
import os
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class AgentToolPolicy:
    """Tool policy configuration per agent."""
    allowlist: List[str] = field(default_factory=list)
    denylist: List[str] = field(default_factory=list)
    groups: Dict[str, List[str]] = field(default_factory=dict)
    sandbox_mode: str = "off"
    sandbox_scope: str = "session"
    workspace_access: str = "ro"


@dataclass
class AgentBootstrapConfig:
    """Bootstrap file paths per agent."""
    soul_path: Optional[str] = None
    identity_path: Optional[str] = None
    memory_path: Optional[str] = None
    skills_path: Optional[str] = None
    heartbeat_path: Optional[str] = None
    skill_filter: Optional[List[str]] = None
    bootstrap_max_chars: int = 20000
    bootstrap_total_max_chars: int = 50000


@dataclass
class AgentSessionScope:
    """Session scoping configuration per agent."""
    default_scope: str = "main"
    dm_scope: str = "per-peer"
    group_scope: str = "per-channel-peer"


@dataclass
class EnhancedAgentConfig:
    """Enhanced agent configuration from AGENTS.md."""
    name: str
    model: str
    temperature: float
    max_tokens: int
    system_prompt: str
    tool_policy: AgentToolPolicy = field(default_factory=AgentToolPolicy)
    bootstrap: AgentBootstrapConfig = field(default_factory=AgentBootstrapConfig)
    session_scope: AgentSessionScope = field(default_factory=AgentSessionScope)


class AgentsConfig:
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.expanduser("~/.wanclaw/AGENTS.md")
        self.config_path = Path(config_path)
        self.agents: List[Dict] = []
        self._load()

    def _load(self):
        if not self.config_path.exists():
            self.agents = self._default_agents()
            self.save()
            return
        try:
            content = self.config_path.read_text(encoding="utf-8")
            self.agents = self._parse_agents_md(content)
        except Exception as e:
            logger.error(f"AGENTS.md load error: {e}")
            self.agents = self._default_agents()

    def _parse_agents_md(self, content: str) -> List[Dict]:
        agents = []
        current = None
        for line in content.split("\n"):
            line = line.rstrip()
            if line.startswith("## ") and not line.startswith("###"):
                name = line[3:].strip()
                current = {"name": name, "description": "", "soul": "", "tools": [], "enabled": True}
            elif current and line.startswith("###"):
                key_val = line[4:].strip()
                if ": " in key_val:
                    k, v = key_val.split(": ", 1)
                    k = k.strip().lower().replace(" ", "_")
                    if k == "soul_file":
                        k = "soul"
                        try:
                            v = Path(self.config_path.parent / v.strip()).read_text()
                        except Exception:
                            pass
                    if k == "tools":
                        v = [t.strip() for t in v.split(",")]
                    if k == "enabled":
                        v = v.strip().lower() in ("true", "yes", "1")
                    current[k] = v
                elif key_val.lower() == "description":
                    pass
            elif current and line.startswith("- "):
                tool = line[2:].strip()
                if tool:
                    current.setdefault("tools", []).append(tool)
            elif current and not line.startswith("#") and not line.startswith("-"):
                if line.strip():
                    current["description"] = (current.get("description", "") + " " + line.strip()).strip()
            elif current and (not line or line.startswith("#")):
                if current.get("name"):
                    agents.append(current)
                current = None
        if current and current.get("name"):
            agents.append(current)
        return agents if agents else self._default_agents()

    def _default_agents(self) -> List[Dict]:
        return [{
            "name": "WanClaw",
            "description": "Default multi-platform AI assistant",
            "soul": "",
            "tools": [],
            "enabled": True,
        }]

    def save(self):
        lines = ["# AGENTS.md — WanClaw Agent Configuration\n"]
        for agent in self.agents:
            lines.append(f"## {agent['name']}\n")
            lines.append(f"description: {agent.get('description', '')}\n")
            if agent.get("soul"):
                lines.append(f"soul_file: SOUL.{agent['name']}.md\n")
            if agent.get("tools"):
                lines.append(f"tools: {', '.join(agent['tools'])}\n")
            lines.append(f"enabled: {'true' if agent.get('enabled', True) else 'false'}\n")
            lines.append("\n")
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text("".join(lines), encoding="utf-8")
        logger.info(f"AGENTS.md saved with {len(self.agents)} agents")

    def get_agent(self, name: str) -> Optional[Dict]:
        for a in self.agents:
            if a["name"] == name:
                return a
        return self.agents[0] if self.agents else None

    def list_agents(self) -> List[Dict]:
        return list(self.agents)

    def add_agent(self, agent: Dict) -> bool:
        if any(a["name"] == agent["name"] for a in self.agents):
            return False
        self.agents.append(agent)
        self.save()
        return True

    def remove_agent(self, name: str) -> bool:
        before = len(self.agents)
        self.agents = [a for a in self.agents if a["name"] != name]
        if len(self.agents) < before:
            self.save()
            return True
        return False

    def enable_agent(self, name: str, enabled: bool = True):
        for a in self.agents:
            if a["name"] == name:
                a["enabled"] = enabled
        self.save()

    def get_agent_config(self, agent_id: str = "main") -> EnhancedAgentConfig:
        base = self.get_agent(agent_id)
        if not base:
            return self._default_enhanced_config(agent_id)
        enhanced = self._parse_enhanced_fields(base)
        return EnhancedAgentConfig(
            name=base.get("name", agent_id),
            model=base.get("model", "gpt-4o"),
            temperature=float(base.get("temperature", 0.7)),
            max_tokens=int(base.get("max_tokens", 4096)),
            system_prompt=base.get("description", "You are a helpful AI assistant."),
            **enhanced
        )

    def _parse_enhanced_fields(self, agent: Dict) -> Dict[str, Any]:
        result = {}
        content = self.config_path.read_text(encoding="utf-8") if self.config_path.exists() else ""
        agent_name = agent.get("name", "")
        tool_policy_match = re.search(
            rf"##\s+{re.escape(agent_name)}\s*>\s*tool_policy\s*\n(.*?)(?=\n##|\Z)",
            content, re.DOTALL | re.IGNORECASE
        )
        if tool_policy_match:
            result["tool_policy"] = self._parse_yaml_block(tool_policy_match.group(1), AgentToolPolicy)
        bootstrap_match = re.search(
            rf"##\s+{re.escape(agent_name)}\s*>\s*bootstrap\s*\n(.*?)(?=\n##|\Z)",
            content, re.DOTALL | re.IGNORECASE
        )
        if bootstrap_match:
            result["bootstrap"] = self._parse_yaml_block(bootstrap_match.group(1), AgentBootstrapConfig)
        session_scope_match = re.search(
            rf"##\s+{re.escape(agent_name)}\s*>\s*session_scope\s*\n(.*?)(?=\n##|\Z)",
            content, re.DOTALL | re.IGNORECASE
        )
        if session_scope_match:
            result["session_scope"] = self._parse_yaml_block(session_scope_match.group(1), AgentSessionScope)
        return result

    def _parse_yaml_block(self, text: str, cls):
        data = {}
        current_list: Optional[str] = None
        current_items: List[str] = []
        for line in text.split("\n"):
            if line.strip().startswith("```"):
                continue
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("- "):
                if current_list:
                    data[current_list] = list(current_items)
                    current_items = []
                current_list = data.get("_last_key", "")
                if current_list:
                    current_items.append(stripped[2:].strip('"').strip("'"))
                    current_list = "_list"
                else:
                    current_list = "_list"
                    current_items = [stripped[2:].strip('"').strip("'")]
            elif ": " in stripped:
                if current_list and current_list != "_list":
                    data[current_list] = list(current_items)
                    current_items = []
                elif current_list == "_list" and data.get("_last_key"):
                    data[data["_last_key"]] = list(current_items)
                    current_items = []
                    current_list = None
                k, v = stripped.split(": ", 1)
                k = k.strip()
                v = v.strip()
                v_stripped = v.strip('"').strip("'")
                if v_stripped.lower() == "true":
                    data[k] = True
                elif v_stripped.lower() == "false":
                    data[k] = False
                elif v_stripped.lstrip("-").isdigit():
                    data[k] = int(v_stripped.lstrip("-"))
                elif v_stripped.replace(".", "", 1).isdigit():
                    data[k] = float(v_stripped)
                else:
                    data[k] = v_stripped
                data["_last_key"] = k
                current_list = k
            elif stripped.endswith(":") and not ": " in stripped:
                k = stripped[:-1].strip()
                data["_last_key"] = k
                current_list = k
        if current_list and current_list != "_list" and current_items:
            data[current_list] = list(current_items)
        for drop in [k for k in data if k.startswith("_")]:
            del data[drop]
        try:
            kwargs = {}
            for f in cls.__dataclass_fields__.values():
                if f.name in data:
                    kwargs[f.name] = data[f.name]
                elif f.name == "skill_filter" and "skill_filter" in data:
                    kwargs[f.name] = data["skill_filter"]
                elif f.name == "bootstrap_max_chars" and "bootstrap_max_chars" in data:
                    kwargs[f.name] = int(data["bootstrap_max_chars"])
                elif f.name == "bootstrap_total_max_chars" and "bootstrap_total_max_chars" in data:
                    kwargs[f.name] = int(data["bootstrap_total_max_chars"])
            return cls(**kwargs)
        except Exception:
            return cls()

    def _default_enhanced_config(self, agent_id: str) -> EnhancedAgentConfig:
        return EnhancedAgentConfig(
            name=agent_id,
            model="gpt-4o",
            temperature=0.7,
            max_tokens=4096,
            system_prompt="You are a helpful AI assistant.",
        )


_agents_config: Optional[AgentsConfig] = None


def get_agents_config() -> AgentsConfig:
    global _agents_config
    if _agents_config is None:
        _agents_config = AgentsConfig()
    return _agents_config
