"""
Tests for Tool Policy Engine.

Validates allow/deny list evaluation, group expansion,
deny-wins semantics, per-skill tool requirements,
sandbox nested policy, and skill enable/disable.
"""
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def base_policy() -> dict:
    """Base global policy dict."""
    return {
        "allow": ["read", "write", "grep"],
        "deny": [],
        "groups": {
            "runtime": ["exec", "bash", "process"],
            "filesystem": ["read", "write", "delete"],
        },
    }


@pytest.fixture
def skill_requirements() -> dict:
    """Per-skill tool requirements extracted from SKILL.md."""
    return {
        "skill_a": {"tools": ["bash", "write", "read"]},
        "skill_b": {"tools": ["exec", "process"]},
    }


# ---------------------------------------------------------------------------
# Tests — Allow/Deny List Evaluation
# ---------------------------------------------------------------------------

class TestAllowDenyEvaluation:
    """Tool access is evaluated against allow and deny lists."""

    def test_allowed_tool_passes(self, base_policy):
        """Tools in allow list are permitted."""
        from wanclaw.agent.tool_policy import ToolPolicy

        policy = ToolPolicy(base_policy)
        assert policy.allows("read") is True
        assert policy.allows("write") is True
        assert policy.allows("grep") is True

    def test_unlisted_tool_denied(self, base_policy):
        """Tools not in allow list are denied."""
        from wanclaw.agent.tool_policy import ToolPolicy

        policy = ToolPolicy(base_policy)
        assert policy.allows("delete") is False
        assert policy.allows("exec") is False

    def test_denied_tool_blocked(self):
        """Tools explicitly in deny list are blocked."""
        policy_dict = {"allow": ["read", "write"], "deny": ["read"]}
        from wanclaw.agent.tool_policy import ToolPolicy

        policy = ToolPolicy(policy_dict)
        assert policy.allows("read") is False

    def test_empty_allow_means_all_denied(self):
        """Empty allow list denies all tools."""
        policy_dict = {"allow": [], "deny": []}
        from wanclaw.agent.tool_policy import ToolPolicy

        policy = ToolPolicy(policy_dict)
        assert policy.allows("read") is False
        assert policy.allows("write") is False

    def test_empty_deny_is无害(self):
        """Empty deny list with populated allow works correctly."""
        policy_dict = {"allow": ["read", "write"], "deny": []}
        from wanclaw.agent.tool_policy import ToolPolicy

        policy = ToolPolicy(policy_dict)
        assert policy.allows("read") is True
        assert policy.allows("write") is True


# ---------------------------------------------------------------------------
# Tests — Group Expansion
# ---------------------------------------------------------------------------

class TestGroupExpansion:
    """Tool groups expand to their member tools."""

    def test_group_expands_runtime(self, base_policy):
        """group:runtime expands to exec, bash, process."""
        from wanclaw.agent.tool_policy import ToolPolicy

        policy = ToolPolicy(base_policy)
        expanded = policy.expand_groups(["group:runtime"])
        assert "exec" in expanded
        assert "bash" in expanded
        assert "process" in expanded

    def test_group_expands_filesystem(self, base_policy):
        """group:filesystem expands to read, write, delete."""
        from wanclaw.agent.tool_policy import ToolPolicy

        policy = ToolPolicy(base_policy)
        expanded = policy.expand_groups(["group:filesystem"])
        assert "read" in expanded
        assert "write" in expanded
        assert "delete" in expanded

    def test_mixed_group_and_direct(self, base_policy):
        """Mixing group references and direct tool names works."""
        from wanclaw.agent.tool_policy import ToolPolicy

        policy = ToolPolicy(base_policy)
        expanded = policy.expand_groups(["read", "group:runtime"])
        assert "read" in expanded
        assert "bash" in expanded

    def test_unknown_group_ignored(self, base_policy):
        """Unknown group names are ignored without error."""
        from wanclaw.agent.tool_policy import ToolPolicy

        policy = ToolPolicy(base_policy)
        expanded = policy.expand_groups(["group:nonexistent", "read"])
        assert "read" in expanded
        assert "group:nonexistent" not in expanded


# ---------------------------------------------------------------------------
# Tests — Deny Wins Over Allow
# ---------------------------------------------------------------------------

class TestDenyWins:
    """Deny list takes precedence over allow list."""

    def test_explicit_deny_overrides_allow(self):
        """If a tool is in both allow and deny, deny wins."""
        policy_dict = {"allow": ["read", "write", "exec"], "deny": ["read"]}
        from wanclaw.agent.tool_policy import ToolPolicy

        policy = ToolPolicy(policy_dict)
        assert policy.allows("read") is False
        assert policy.allows("write") is True
        assert policy.allows("exec") is True

    def test_deny_in_group_wins(self):
        """Deny applies even when allow used group expansion."""
        policy_dict = {
            "allow": ["read", "write", "group:runtime"],
            "deny": ["exec"],
            "groups": {"runtime": ["exec", "bash", "process"]},
        }
        from wanclaw.agent.tool_policy import ToolPolicy

        policy = ToolPolicy(policy_dict)
        # deny takes precedence
        assert policy.allows("exec") is False
        # bash and process still allowed (not in deny)
        assert policy.allows("bash") is True
        assert policy.allows("process") is True

    def test_multiple_denies_all_blocked(self):
        """Multiple tools in deny list are all blocked."""
        policy_dict = {"allow": ["read", "write", "grep"], "deny": ["read", "write"]}
        from wanclaw.agent.tool_policy import ToolPolicy

        policy = ToolPolicy(policy_dict)
        assert policy.allows("read") is False
        assert policy.allows("write") is False
        assert policy.allows("grep") is True


# ---------------------------------------------------------------------------
# Tests — Per-Skill Tool Requirements
# ---------------------------------------------------------------------------

class TestPerSkillRequirements:
    """Per-skill requirements from SKILL.md restrict available tools."""

    def test_skill_restricts_tools(self, skill_requirements):
        """Skill's required tools override the global allow list."""
        from wanclaw.agent.tool_policy import ToolPolicy

        policy = ToolPolicy(
            {"allow": ["read", "write", "grep"], "deny": []},
            skill_requirements=skill_requirements,
        )
        # skill_a requires bash, write, read
        allowed_a = policy.get_allowed_tools("skill_a")
        assert "bash" in allowed_a
        assert "write" in allowed_a
        # grep not in skill_a's requirements
        assert "grep" not in allowed_a

    def test_skill_b_requires_exec_process(self, skill_requirements):
        """skill_b requires exec and process."""
        from wanclaw.agent.tool_policy import ToolPolicy

        policy = ToolPolicy(
            {"allow": ["read", "write"], "deny": []},
            skill_requirements=skill_requirements,
        )
        allowed_b = policy.get_allowed_tools("skill_b")
        assert "exec" in allowed_b
        assert "process" in allowed_b

    def test_unknown_skill_falls_back_to_global(self, skill_requirements):
        """Skill not in requirements dict falls back to global policy."""
        from wanclaw.agent.tool_policy import ToolPolicy

        policy = ToolPolicy(
            {"allow": ["read", "write"], "deny": []},
            skill_requirements=skill_requirements,
        )
        allowed = policy.get_allowed_tools("unknown_skill")
        assert "read" in allowed
        assert "write" in allowed


# ---------------------------------------------------------------------------
# Tests — Sandbox Nested Policy
# ---------------------------------------------------------------------------

class TestSandboxNestedPolicy:
    """SKILL.md sandbox section creates nested policy scope."""

    def test_sandbox_allowed_tools(self):
        """sandbox.allowed restricts tools inside sandbox."""
        policy_dict = {
            "allow": ["bash", "read", "write", "delete", "exec"],
            "deny": [],
            "sandbox": {"allowed": ["bash", "read"]},
        }
        from wanclaw.agent.tool_policy import ToolPolicy

        policy = ToolPolicy(policy_dict)
        sandbox_policy = policy.get_sandbox_policy()
        assert sandbox_policy.allows("bash") is True
        assert sandbox_policy.allows("read") is True
        assert sandbox_policy.allows("delete") is False
        assert sandbox_policy.allows("exec") is False

    def test_sandbox_denied_tools(self):
        """sandbox.denylist blocks specific tools inside sandbox."""
        policy_dict = {
            "allow": ["bash", "read", "write", "delete"],
            "deny": [],
            "sandbox": {"denied": ["delete"]},
        }
        from wanclaw.agent.tool_policy import ToolPolicy

        policy = ToolPolicy(policy_dict)
        sandbox_policy = policy.get_sandbox_policy()
        assert sandbox_policy.allows("delete") is False

    def test_sandbox_inherits_global_deny(self):
        """Global deny list applies inside sandbox too."""
        policy_dict = {
            "allow": ["bash", "read", "write"],
            "deny": ["bash"],
            "sandbox": {"allowed": ["bash", "read"]},
        }
        from wanclaw.agent.tool_policy import ToolPolicy

        policy = ToolPolicy(policy_dict)
        sandbox_policy = policy.get_sandbox_policy()
        # Global deny still applies in sandbox
        assert sandbox_policy.allows("bash") is False

    def test_no_sandbox_returns_global_policy(self):
        """When no sandbox section, get_sandbox_policy returns self."""
        from wanclaw.agent.tool_policy import ToolPolicy

        policy = ToolPolicy({"allow": ["read", "write"], "deny": []})
        sandbox_policy = policy.get_sandbox_policy()
        assert sandbox_policy is policy


# ---------------------------------------------------------------------------
# Tests — Skill Enable/Disable
# ---------------------------------------------------------------------------

class TestSkillEnableDisable:
    """Skills can be enabled or disabled via policy."""

    def test_disabled_skill_all_tools_denied(self, skill_requirements):
        """Disabled skill denies all tools."""
        from wanclaw.agent.tool_policy import ToolPolicy

        policy = ToolPolicy(
            {"allow": ["read", "write", "bash"], "deny": []},
            skill_requirements=skill_requirements,
            disabled_skills={"skill_a"},
        )
        allowed_a = policy.get_allowed_tools("skill_a")
        assert len(allowed_a) == 0 or (
            all(policy.allows(t) is False for t in skill_requirements["skill_a"]["tools"])
        )

    def test_enabled_skill_unaffected(self, skill_requirements):
        """Enabled (non-disabled) skill works normally."""
        from wanclaw.agent.tool_policy import ToolPolicy

        policy = ToolPolicy(
            {"allow": ["read", "write", "bash"], "deny": []},
            skill_requirements=skill_requirements,
            disabled_skills={"skill_b"},
        )
        allowed_a = policy.get_allowed_tools("skill_a")
        assert "bash" in allowed_a
        assert "write" in allowed_a

    def test_empty_disabled_set_allows_all(self, skill_requirements):
        """Empty disabled_skills set means all skills allowed."""
        from wanclaw.agent.tool_policy import ToolPolicy

        policy = ToolPolicy(
            {"allow": ["read", "write", "bash"], "deny": []},
            skill_requirements=skill_requirements,
            disabled_skills=set(),
        )
        allowed_a = policy.get_allowed_tools("skill_a")
        assert "bash" in allowed_a

    def test_disable_unknown_skill_no_error(self):
        """Disabling an unknown skill does not raise."""
        from wanclaw.agent.tool_policy import ToolPolicy

        policy = ToolPolicy(
            {"allow": ["read", "write"], "deny": []},
            disabled_skills={"nonexistent_skill"},
        )
        # Should not raise
        allowed = policy.get_allowed_tools("nonexistent_skill")
        assert isinstance(allowed, (list, set))
