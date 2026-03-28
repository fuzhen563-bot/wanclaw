"""
Tests for Skill Prompt Limits — truncation, compact format, relevance selection,
and binary search for fitting skills within budget.

Validates maxSkillsInPrompt truncation, maxSkillFileBytes truncation,
compact format (name + description + ## Usage), skill relevance selection,
and binary search for max skills that fit budget.
"""
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def large_skill_registry() -> list[dict]:
    """Skill registry with varying sizes and topics."""
    return [
        {
            "name": "git_master",
            "description": "Git operations, commit, branch management",
            "content": "# Git Master\n\n" + "Git is a version control system.\n" * 200,
            "tokens": 2000,
            "keywords": ["git", "commit", "branch", "merge"],
        },
        {
            "name": "code_review",
            "description": "Code review, PR feedback, best practices",
            "content": "# Code Review\n\n" + "Code review improves quality.\n" * 150,
            "tokens": 1500,
            "keywords": ["code", "review", "pr", "pull request"],
        },
        {
            "name": "docker_skill",
            "description": "Docker containerization, images, docker-compose",
            "content": "# Docker Skill\n\n" + "Docker containers wrap software.\n" * 100,
            "tokens": 1000,
            "keywords": ["docker", "container", "image", "compose"],
        },
        {
            "name": "python_dev",
            "description": "Python development, async, typing",
            "content": "# Python Dev\n\n" + "Python is a programming language.\n" * 80,
            "tokens": 800,
            "keywords": ["python", "async", "type"],
        },
        {
            "name": "bash_script",
            "description": "Bash scripting, shell commands",
            "content": "# Bash Script\n\n" + "Bash is a Unix shell.\n" * 60,
            "tokens": 600,
            "keywords": ["bash", "shell", "script"],
        },
        {
            "name": "web_frontend",
            "description": "HTML, CSS, JavaScript frontend development",
            "content": "# Web Frontend\n\n" + "Frontend web development.\n" * 50,
            "tokens": 500,
            "keywords": ["html", "css", "javascript", "frontend"],
        },
    ]


# ---------------------------------------------------------------------------
# Tests — maxSkillsInPrompt Truncation
# ---------------------------------------------------------------------------

class TestMaxSkillsInPrompt:
    """Enforces maxSkillsInPrompt limit on included skills."""

    def test_truncates_to_max_skills(self, large_skill_registry: list[dict]):
        """select_skills() returns at most maxSkillsInPrompt skills."""
        from wanclaw.agent.skill_prompt_limits import select_skills

        selected = select_skills(
            skills=large_skill_registry,
            max_skills=3,
            user_input="I need help with docker",
            max_tokens=100000,
        )
        assert len(selected) <= 3

    def test_respects_exact_limit(self, large_skill_registry: list[dict]):
        """select_skills() returns exactly max_skills when more available."""
        from wanclaw.agent.skill_prompt_limits import select_skills

        selected = select_skills(
            skills=large_skill_registry,
            max_skills=4,
            user_input="",
            max_tokens=100000,
        )
        assert len(selected) == 4

    def test_returns_all_when_under_limit(self, large_skill_registry: list[dict]):
        """select_skills() returns all skills when fewer than max_skills."""
        from wanclaw.agent.skill_prompt_limits import select_skills

        selected = select_skills(
            skills=large_skill_registry[:2],
            max_skills=5,
            user_input="",
            max_tokens=100000,
        )
        assert len(selected) == 2


# ---------------------------------------------------------------------------
# Tests — maxSkillFileBytes Truncation
# ---------------------------------------------------------------------------

class TestMaxSkillFileBytes:
    """Large skill content is truncated to maxSkillFileBytes."""

    def test_large_skill_truncated(self, large_skill_registry: list[dict]):
        """select_skills() truncates content of large skills."""
        from wanclaw.agent.skill_prompt_limits import select_skills

        selected = select_skills(
            skills=large_skill_registry,
            max_skills=1,
            max_skill_file_bytes=500,
            user_input="",
            max_tokens=100000,
        )
        assert len(selected) == 1
        skill = selected[0]
        content = skill.get("content", "") or skill.get("body", "")
        assert len(content) <= 600, "Content should be truncated to ~max_skill_file_bytes"

    def test_small_skill_not_truncated(self, large_skill_registry: list[dict]):
        """Skills under max_skill_file_bytes are kept intact."""
        from wanclaw.agent.skill_prompt_limits import select_skills

        selected = select_skills(
            skills=large_skill_registry,
            max_skills=1,
            max_skill_file_bytes=10000,
            user_input="",
            max_tokens=100000,
        )
        assert len(selected) == 1
        # Small skill (python_dev or bash_script) should be kept full
        skill = selected[0]
        content = skill.get("content", "") or skill.get("body", "")
        assert len(content) > 500, "Small skill should not be truncated"

    def test_truncation_preserves_skill_name(self, large_skill_registry: list[dict]):
        """Truncated skill retains its name and description."""
        from wanclaw.agent.skill_prompt_limits import select_skills

        selected = select_skills(
            skills=large_skill_registry,
            max_skills=1,
            max_skill_file_bytes=200,
            user_input="",
            max_tokens=100000,
        )
        skill = selected[0]
        assert "name" in skill
        assert "description" in skill
        # Name and description should be intact even with truncated body
        assert len(skill["name"]) > 0


# ---------------------------------------------------------------------------
# Tests — Compact Format
# ---------------------------------------------------------------------------

class TestCompactFormat:
    """Compact format keeps name + description + ## Usage only."""

    def test_compact_format_structure(self, large_skill_registry: list[dict]):
        """compact_format() returns name + description + ## Usage."""
        from wanclaw.agent.skill_prompt_limits import compact_format

        skill = large_skill_registry[0]  # git_master
        compact = compact_format(skill)

        assert isinstance(compact, str)
        assert skill["name"] in compact
        assert skill["description"] in compact
        assert "## Usage" in compact or "# Usage" in compact

    def test_compact_format_removes_details(self, large_skill_registry: list[dict]):
        """compact_format() removes detailed body content."""
        from wanclaw.agent.skill_prompt_limits import compact_format

        skill = large_skill_registry[0]  # git_master with 200 lines
        compact = compact_format(skill)

        # Should be much shorter than full content
        assert len(compact) < len(skill["content"]) // 5

    def test_compact_applied_when_flag_set(self, large_skill_registry: list[dict]):
        """compact=True in select_skills applies compact_format to all."""
        from wanclaw.agent.skill_prompt_limits import select_skills

        selected = select_skills(
            skills=large_skill_registry[:2],
            max_skills=2,
            compact=True,
            user_input="",
            max_tokens=100000,
        )
        for skill in selected:
            content = skill.get("content", "") or skill.get("body", "")
            # Compact format should be much shorter
            assert len(content) < 500, "Compact format should be concise"


# ---------------------------------------------------------------------------
# Tests — Skill Relevance Selection
# ---------------------------------------------------------------------------

class TestSkillRelevanceSelection:
    """Skills matching user input keywords are prioritized."""

    def test_git_keyword_selects_git_skill(self, large_skill_registry: list[dict]):
        """User input with 'git' keyword selects git_master skill."""
        from wanclaw.agent.skill_prompt_limits import select_skills

        selected = select_skills(
            skills=large_skill_registry,
            max_skills=2,
            user_input="How do I commit with git?",
            max_tokens=100000,
        )
        names = [s["name"] for s in selected]
        assert "git_master" in names, "git_master should be selected for 'git' keyword"

    def test_docker_keyword_selects_docker_skill(
        self, large_skill_registry: list[dict]
    ):
        """User input with 'docker' keyword selects docker_skill."""
        from wanclaw.agent.skill_prompt_limits import select_skills

        selected = select_skills(
            skills=large_skill_registry,
            max_skills=2,
            user_input="Run this in a docker container",
            max_tokens=100000,
        )
        names = [s["name"] for s in selected]
        assert "docker_skill" in names

    def test_multiple_keywords_select_multiple_relevant(
        self, large_skill_registry: list[dict]
    ):
        """Multiple keywords select multiple relevant skills within limit."""
        from wanclaw.agent.skill_prompt_limits import select_skills

        selected = select_skills(
            skills=large_skill_registry,
            max_skills=3,
            user_input="git commit and docker build",
            max_tokens=100000,
        )
        names = [s["name"] for s in selected]
        assert "git_master" in names
        assert "docker_skill" in names

    def test_no_keyword_returns_top_n(self, large_skill_registry: list[dict]):
        """No keyword match returns first N skills (deterministic order)."""
        from wanclaw.agent.skill_prompt_limits import select_skills

        selected = select_skills(
            skills=large_skill_registry,
            max_skills=2,
            user_input="",  # No keyword
            max_tokens=100000,
        )
        # Should not raise, just return first N
        assert len(selected) == 2
        # Results should be deterministic (same order each time)
        selected_again = select_skills(
            skills=large_skill_registry,
            max_skills=2,
            user_input="",
            max_tokens=100000,
        )
        assert [s["name"] for s in selected] == [s["name"] for s in selected_again]


# ---------------------------------------------------------------------------
# Tests — Binary Search for Max Skills
# ---------------------------------------------------------------------------

class TestBinarySearchForMaxSkills:
    """Binary search finds the maximum number of skills fitting budget."""

    def test_binary_search_finds_max_fitting(
        self, large_skill_registry: list[dict]
    ):
        """find_max_skills() uses binary search to maximize skills within budget."""
        from wanclaw.agent.skill_prompt_limits import find_max_skills

        # Budget that allows ~3 skills but not all 6
        max_tokens = 4000
        max_count = find_max_skills(
            skills=large_skill_registry,
            max_tokens=max_tokens,
            max_skills=6,
        )
        # Should find some maximum (between 1 and 6)
        assert 1 <= max_count <= 6

        # Verify the count actually fits
        from wanclaw.agent.skill_prompt_limits import select_skills

        selected = select_skills(
            skills=large_skill_registry,
            max_skills=max_count,
            user_input="",
            max_tokens=max_tokens,
        )
        total_tokens = sum(s.get("tokens", 100) for s in selected)
        assert total_tokens <= max_tokens

    def test_binary_search_within_budget(self, large_skill_registry: list[dict]):
        """find_max_skills() result is within budget."""
        from wanclaw.agent.skill_prompt_limits import find_max_skills

        max_tokens = 3000
        max_count = find_max_skills(
            skills=large_skill_registry,
            max_tokens=max_tokens,
            max_skills=len(large_skill_registry),
        )

        # Binary search should not exceed available skills
        assert max_count <= len(large_skill_registry)
        assert max_count >= 1

    def test_binary_search_returns_zero_for_zero_budget(
        self, large_skill_registry: list[dict]
    ):
        """find_max_skills() returns 0 for zero budget."""
        from wanclaw.agent.skill_prompt_limits import find_max_skills

        max_count = find_max_skills(
            skills=large_skill_registry,
            max_tokens=0,
            max_skills=6,
        )
        assert max_count == 0

    def test_binary_search_returns_all_when_budget_sufficient(
        self, large_skill_registry: list[dict]
    ):
        """find_max_skills() returns all skills when budget is generous."""
        from wanclaw.agent.skill_prompt_limits import find_max_skills

        max_count = find_max_skills(
            skills=large_skill_registry,
            max_tokens=100000,
            max_skills=len(large_skill_registry),
        )
        assert max_count == len(large_skill_registry)
