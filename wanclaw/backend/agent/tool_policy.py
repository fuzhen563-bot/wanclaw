"""
Tool Policy Engine — allow/deny evaluation, group expansion, per-skill requirements.

Provides ToolPolicy for evaluating tool access against a structured policy dict.
Deny always wins over allow. Groups expand at check time. Per-skill requirements
override global policy. Sandbox policies nest within the global scope.
"""
from typing import Dict, List, Optional, Set, Any


class ToolPolicy:
    """
    Evaluates tool access against an allow/deny policy.

    Policy dict format:
    {
        "allow": ["tool", "group:group_name", ...],
        "deny": ["tool", ...],
        "groups": {"group_name": ["tool", ...]},
        "sandbox": {"allowed": [...], "denied": [...]},
    }

    Deny wins over allow. Groups are expanded at check time.
    """

    def __init__(
        self,
        policy: Dict[str, Any],
        skill_requirements: Optional[Dict[str, Dict[str, List[str]]]] = None,
        disabled_skills: Optional[Set[str]] = None,
    ):
        self.policy = policy
        self.skill_requirements = skill_requirements or {}
        self.disabled_skills = disabled_skills or set()

    def expand_groups(self, tools: List[str]) -> List[str]:
        """Expand group:X references to their member tools."""
        groups = self.policy.get("groups", {})
        result: List[str] = []
        for tool in tools:
            if tool.startswith("group:"):
                name = tool[len("group:") :]
                members = groups.get(name, [])
                result.extend(members)
            else:
                result.append(tool)
        return result

    def _effective_allow(self) -> Set[str]:
        raw = self.policy.get("allow", [])
        expanded = self.expand_groups(raw)
        deny_set = set(self.policy.get("deny", []))
        return set(expanded) - deny_set

    def allows(self, tool: str) -> bool:
        """Return True if tool is allowed."""
        effective = self._effective_allow()
        if self.policy.get("allow") is not None and len(self.policy["allow"]) == 0:
            return False
        return tool in effective

    def get_allowed_tools(self, skill: str) -> List[str]:
        """Return tools allowed for a given skill, considering per-skill requirements.

        Skill requirements define the EXACT allowed set for that skill (override global allow).
        Deny list always applies.
        """
        if skill in self.disabled_skills:
            return []

        if skill in self.skill_requirements:
            skill_tools = set(self.skill_requirements[skill].get("tools", []))
            deny_set = set(self.policy.get("deny", []))
            return sorted(skill_tools - deny_set)

        effective = self._effective_allow()
        return sorted(effective)

    def get_sandbox_policy(self) -> "ToolPolicy":
        """Return a nested policy for sandbox execution."""
        sandbox = self.policy.get("sandbox")
        if not sandbox:
            return self

        sandbox_allow = sandbox.get("allowed")
        sandbox_deny = sandbox.get("denied", [])

        if sandbox_allow is None:
            nested: Dict[str, Any] = {
                "allow": list(self._effective_allow()),
                "deny": list(set(sandbox_deny) | set(self.policy.get("deny", []))),
            }
        else:
            nested = {
                "allow": list(sandbox_allow),
                "deny": list(
                    set(sandbox_deny) | set(self.policy.get("deny", []))
                ),
            }

        return ToolPolicy(nested)
