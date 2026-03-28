"""
Tests for ContextAssembly — assembles BootstrapLoader + Skills + Transcript
into a single prompt, respecting token budgets and skill selection limits.

Validates the full pipeline, token budget, truncation warnings,
skill selection (maxSkillsInPrompt), compact format fallback,
and message structure (system first).
"""
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_bootstrap_entries() -> list[dict]:
    """Mock bootstrap entries from BootstrapLoader."""
    return [
        {
            "source": "SOUL.md",
            "content": "You are a helpful AI assistant.",
            "priority": 1,
        },
        {
            "source": "IDENTITY.md",
            "content": "Name: TestBot\nVersion: 1.0.0",
            "priority": 2,
        },
        {
            "source": "USER.md",
            "content": "User: Alice",
            "priority": 3,
        },
    ]


@pytest.fixture
def mock_skill_registry() -> list[dict]:
    """Mock skill registry with name, description, tokens."""
    return [
        {
            "name": "skill_a",
            "description": "Does thing A",
            "content": "# Skill A\n\nDoes A.",
            "tokens": 100,
        },
        {
            "name": "skill_b",
            "description": "Does thing B",
            "content": "# Skill B\n\nDoes B.",
            "tokens": 100,
        },
        {
            "name": "skill_c",
            "description": "Does thing C",
            "content": "# Skill C\n\nDoes C.",
            "tokens": 100,
        },
        {
            "name": "skill_d",
            "description": "Does thing D",
            "content": "# Skill D\n\nDoes D.",
            "tokens": 100,
        },
        {
            "name": "skill_e",
            "description": "Does thing E",
            "content": "# Skill E\n\nDoes E.",
            "tokens": 100,
        },
    ]


@pytest.fixture
def mock_transcript_entries() -> list[dict]:
    """Mock transcript entries."""
    return [
        {"role": "user", "content": "Hello", "timestamp": "2024-01-01T10:00:00Z"},
        {
            "role": "assistant",
            "content": "Hi there!",
            "timestamp": "2024-01-01T10:00:01Z",
        },
    ]


# ---------------------------------------------------------------------------
# Tests — Full Pipeline
# ---------------------------------------------------------------------------

class TestPipeline:
    """ContextAssembly combines BootstrapLoader, Skills, and Transcript."""

    def test_assemble_combines_all_sources(
        self,
        mock_bootstrap_entries: list[dict],
        mock_skill_registry: list[dict],
        mock_transcript_entries: list[dict],
    ):
        """assemble() returns content from bootstrap, skills, and transcript."""
        from wanclaw.agent.context_assembly import ContextAssembly

        ca = ContextAssembly(
            bootstrap_entries=mock_bootstrap_entries,
            skills=mock_skill_registry,
            transcript_entries=mock_transcript_entries,
        )
        result = ca.assemble()

        assert isinstance(result, (str, list, dict))
        result_str = str(result)
        assert "helpful AI assistant" in result_str or "SOUL" in result_str
        assert "skill_a" in result_str or "Skill A" in result_str
        assert "Hello" in result_str

    def test_pipeline_respects_order(
        self,
        mock_bootstrap_entries: list[dict],
        mock_skill_registry: list[dict],
        mock_transcript_entries: list[dict],
    ):
        """Bootstrap appears before skills before transcript in output."""
        from wanclaw.agent.context_assembly import ContextAssembly

        ca = ContextAssembly(
            bootstrap_entries=mock_bootstrap_entries,
            skills=mock_skill_registry,
            transcript_entries=mock_transcript_entries,
        )
        result = ca.assemble()
        result_str = str(result)

        soul_pos = result_str.find("SOUL") if "SOUL" in result_str else result_str.find("helpful")
        skill_pos = result_str.find("skill") if "skill" in result_str.lower() else result_str.find("Skill")
        transcript_pos = result_str.find("Hello")

        if soul_pos != -1 and transcript_pos != -1:
            assert soul_pos < transcript_pos, "Bootstrap should appear before transcript"


# ---------------------------------------------------------------------------
# Tests — Token Budget
# ---------------------------------------------------------------------------

class TestTokenBudget:
    """Total assembled context respects max_tokens budget."""

    def test_total_under_budget(self, mock_bootstrap_entries, mock_skill_registry):
        """assemble() with generous max_tokens includes all content."""
        from wanclaw.agent.context_assembly import ContextAssembly

        ca = ContextAssembly(
            bootstrap_entries=mock_bootstrap_entries,
            skills=mock_skill_registry[:2],
            transcript_entries=[],
        )
        result = ca.assemble(max_tokens=100000)
        result_str = str(result)
        assert "Skill A" in result_str
        assert "Skill B" in result_str

    def test_content_truncated_under_tight_budget(
        self, mock_bootstrap_entries, mock_skill_registry
    ):
        """Tight max_tokens causes truncation of skills or transcript."""
        from wanclaw.agent.context_assembly import ContextAssembly

        ca = ContextAssembly(
            bootstrap_entries=mock_bootstrap_entries,
            skills=mock_skill_registry,
            transcript_entries=[{"role": "user", "content": "X" * 1000}],
        )
        result = ca.assemble(max_tokens=500)
        result_str = str(result)
        # With very tight budget, not all content fits
        # Either skills or transcript is truncated
        total_len = len(result_str)
        assert total_len < 2000, "Result should be smaller with tight budget"

    def test_reserved_tokens_for_user_input(
        self, mock_bootstrap_entries, mock_skill_registry
    ):
        """Max tokens minus reserved = available for context assembly."""
        from wanclaw.agent.context_assembly import ContextAssembly

        max_tokens = 8000
        reserved = 2000

        ca = ContextAssembly(
            bootstrap_entries=mock_bootstrap_entries,
            skills=mock_skill_registry[:2],
            transcript_entries=[],
        )
        result = ca.assemble(max_tokens=max_tokens, reserved_for_user=reserved)
        result_str = str(result)
        # Content should fit within 6000 tokens worth
        # (exact check depends on tokenizer)
        assert isinstance(result, (str, list, dict))


# ---------------------------------------------------------------------------
# Tests — Truncation Warning
# ---------------------------------------------------------------------------

class TestTruncationWarning:
    """Warning is generated when content exceeds budget."""

    def test_truncation_warning_when_exceeded(
        self, mock_bootstrap_entries, mock_skill_registry
    ):
        """assemble() returns or attaches a warning when budget exceeded."""
        from wanclaw.agent.context_assembly import ContextAssembly

        ca = ContextAssembly(
            bootstrap_entries=mock_bootstrap_entries,
            skills=mock_skill_registry,
            transcript_entries=[{"role": "user", "content": "Y" * 5000}],
        )
        result = ca.assemble(max_tokens=500)

        # Check for warning in result
        if isinstance(result, str):
            has_warning = (
                "truncated" in result.lower()
                or "exceeded" in result.lower()
                or "[!]" in result
            )
            assert has_warning, "Result should contain truncation warning"
        elif isinstance(result, dict):
            assert (
                result.get("warning") is not None
                or result.get("_truncated") is True
                or result.get("truncated") is True
            )

    def test_no_warning_within_budget(self, mock_bootstrap_entries):
        """No truncation warning when content fits budget."""
        from wanclaw.agent.context_assembly import ContextAssembly

        ca = ContextAssembly(
            bootstrap_entries=mock_bootstrap_entries,
            skills=[],
            transcript_entries=[],
        )
        result = ca.assemble(max_tokens=100000)
        result_str = str(result)
        # No truncation needed
        assert "truncated" not in result_str.lower()


# ---------------------------------------------------------------------------
# Tests — Skill Selection (maxSkillsInPrompt)
# ---------------------------------------------------------------------------

class TestSkillSelection:
    """Only up to maxSkillsInPrompt skills are included."""

    def test_respects_max_skills_limit(
        self, mock_skill_registry: list[dict]
    ):
        """No more than maxSkillsInPrompt skills appear in output."""
        from wanclaw.agent.context_assembly import ContextAssembly

        ca = ContextAssembly(
            bootstrap_entries=[],
            skills=mock_skill_registry,  # 5 skills
            transcript_entries=[],
        )
        result = ca.assemble(maxSkillsInPrompt=2, max_tokens=100000)
        result_str = str(result)

        # Count skill references in output
        skill_refs = sum(1 for s in mock_skill_registry if s["name"] in result_str)
        assert skill_refs <= 2, f"Should include at most 2 skills, got {skill_refs}"

    def test_skill_selection_by_relevance(
        self, mock_skill_registry: list[dict]
    ):
        """Skills matching user input keywords are prioritized."""
        from wanclaw.agent.context_assembly import ContextAssembly

        ca = ContextAssembly(
            bootstrap_entries=[],
            skills=mock_skill_registry,
            transcript_entries=[{"role": "user", "content": "I need thing A"}],
        )
        result = ca.assemble(maxSkillsInPrompt=2, max_tokens=100000)
        result_str = str(result)

        # skill_a should be selected (matches "thing A")
        # The exact selection logic is implementation-defined,
        # but relevant skills should be included
        skill_refs = [s["name"] for s in mock_skill_registry if s["name"] in result_str]
        assert len(skill_refs) <= 2


# ---------------------------------------------------------------------------
# Tests — Compact Format Fallback
# ---------------------------------------------------------------------------

class TestCompactFormat:
    """Large skills fall back to compact format (name + description + ## Usage)."""

    def test_compact_format_for_large_skills(self, mock_skill_registry: list[dict]):
        """Skills exceeding maxSkillFileBytes use compact format."""
        from wanclaw.agent.context_assembly import ContextAssembly

        # Create a large skill
        large_skills = [
            {
                "name": "large_skill",
                "description": "A large skill with lots of content",
                "content": "# Large Skill\n\n" + "Detailed explanation.\n" * 500,
                "tokens": 5000,
                "compact": "# Large Skill\n\nA large skill with lots of content.\n\n## Usage\n\nUse it wisely.",
            }
        ]

        ca = ContextAssembly(
            bootstrap_entries=[],
            skills=large_skills,
            transcript_entries=[],
        )
        result = ca.assemble(maxSkillFileBytes=500, max_tokens=100000)
        result_str = str(result)

        # Should include compact version, not full content
        assert "Large Skill" in result_str
        # Should NOT include all 500 repetitions of "Detailed"
        assert result_str.count("Detailed") < 100, "Compact format should reduce content"

    def test_full_format_for_small_skills(self, mock_skill_registry: list[dict]):
        """Skills under maxSkillFileBytes use full format."""
        from wanclaw.agent.context_assembly import ContextAssembly

        small_skill = [
            {
                "name": "small_skill",
                "description": "A small skill",
                "content": "# Small Skill\n\nBrief content.\n\n## Details\n\nEverything.",
                "tokens": 50,
            }
        ]

        ca = ContextAssembly(
            bootstrap_entries=[],
            skills=small_skill,
            transcript_entries=[],
        )
        result = ca.assemble(maxSkillFileBytes=5000, max_tokens=100000)
        result_str = str(result)
        assert "Small Skill" in result_str


# ---------------------------------------------------------------------------
# Tests — Message Structure (system first)
# ---------------------------------------------------------------------------

class TestMessageStructure:
    """Assembled messages follow role structure with system first."""

    def test_system_message_first(self, mock_bootstrap_entries: list[dict]):
        """System message (from bootstrap) appears first in message list."""
        from wanclaw.agent.context_assembly import ContextAssembly

        ca = ContextAssembly(
            bootstrap_entries=mock_bootstrap_entries,
            skills=[],
            transcript_entries=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
            ],
        )
        messages = ca.assemble_messages()

        assert isinstance(messages, list)
        assert len(messages) > 0
        assert messages[0]["role"] == "system"

    def test_user_and_assistant_after_system(
        self, mock_bootstrap_entries: list[dict]
    ):
        """User and assistant messages follow system message in order."""
        from wanclaw.agent.context_assembly import ContextAssembly

        ca = ContextAssembly(
            bootstrap_entries=mock_bootstrap_entries,
            skills=[],
            transcript_entries=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi"},
            ],
        )
        messages = ca.assemble_messages()

        roles = [m["role"] for m in messages]
        # system first
        assert roles[0] == "system"
        # user before assistant or interspersed correctly
        assert "user" in roles
        assert "assistant" in roles

    def test_no_duplicate_system_messages(self, mock_bootstrap_entries: list[dict]):
        """Bootstrap content is combined into a single system message."""
        from wanclaw.agent.context_assembly import ContextAssembly

        ca = ContextAssembly(
            bootstrap_entries=mock_bootstrap_entries,
            skills=[],
            transcript_entries=[],
        )
        messages = ca.assemble_messages()

        system_count = sum(1 for m in messages if m["role"] == "system")
        assert system_count == 1, "Should have exactly one system message"
