"""
Tests for SKILL.md YAML frontmatter parsing.

Validates the SkillMarkdownParser class and its extraction of:
- requires.env, requires.bins, requires.config
- primaryEnv, always, os filtering
- user-invocable, disable-model-invocation flags
- install spec (brew/node/uv/download)
- wanclaw extension metadata
- Error handling for malformed frontmatter
"""
import pytest
import yaml


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_frontmatter() -> str:
    return """---
name: my-skill
description: Does amazing things
version: 1.0.0
author: OpenClaw Team
mode: agent

requires:
  env:
    - OPENAI_API_KEY
    - DATABASE_URL
  bins:
    - python3
    - git
  config:
    - log_level

primaryEnv: python3
always: false

os: [linux, darwin]

user-invocable: true
disable-model-invocation: false

install:
  brew:
    - wget
    - curl
  node:
    - typescript
    - ts-node
  uv:
    - requests
    - pyyaml
  download:
    - url: https://example.com/tool.tar.gz
      dest: /usr/local/bin/tool

wanclaw:
  tools: [bash, write, read, grep]
  sandbox:
    allowed: [bash, read]
    denied: [delete, exec]
  maxTokens: 16000
  maxSkillsInPrompt: 3
  maxSkillFileBytes: 20000
  compactFormat: true
---

# My Skill

## Description

Does amazing things with Python.
"""


@pytest.fixture
def minimal_frontmatter() -> str:
    return """---
name: minimal-skill
description: A minimal skill
---

# Minimal Skill
"""


@pytest.fixture
def malformed_yaml_frontmatter() -> str:
    return """---
name: bad-skill
description: [broken yaml array
---

# Bad Skill
"""


@pytest.fixture
def missing_frontmatter_delimiter() -> str:
    return """---
name: no-close
description: Missing closing delimiter

# No Close
"""


@pytest.fixture
def empty_frontmatter() -> str:
    return """# No Frontmatter

Just markdown content.
"""


# ---------------------------------------------------------------------------
# Tests — Parser Interface
# ---------------------------------------------------------------------------

class TestSkillMarkdownParserInterface:
    """Test that SkillMarkdownParser exposes expected methods."""

    def test_parser_has_parse_method(self):
        """Parser must have a parse() classmethod or instance method."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        assert hasattr(SkillMarkdownParser, "parse") or hasattr(
            SkillMarkdownParser, "__call__"
        )

    def test_parse_returns_skill_dict(self, valid_frontmatter: str):
        """parse() returns a dict with expected top-level keys."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        result = SkillMarkdownParser.parse(valid_frontmatter)
        assert isinstance(result, dict)
        assert "name" in result
        assert "description" in result

    def test_parse_preserves_markdown_body(self, valid_frontmatter: str):
        """The markdown body (after closing ---) is preserved."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        result = SkillMarkdownParser.parse(valid_frontmatter)
        assert "body" in result or "markdown" in result or "content" in result
        body = result.get("body") or result.get("markdown") or result.get("content")
        assert "# My Skill" in body


# ---------------------------------------------------------------------------
# Tests — requires Extraction
# ---------------------------------------------------------------------------

class TestRequiresExtraction:
    """Test extraction of requires section from frontmatter."""

    def test_extracts_requires_env(self, valid_frontmatter: str):
        """requires.env list is extracted correctly."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        result = SkillMarkdownParser.parse(valid_frontmatter)
        requires = result.get("requires", {})
        assert "env" in requires
        assert "OPENAI_API_KEY" in requires["env"]
        assert "DATABASE_URL" in requires["env"]

    def test_extracts_requires_bins(self, valid_frontmatter: str):
        """requires.bins list is extracted correctly."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        result = SkillMarkdownParser.parse(valid_frontmatter)
        requires = result.get("requires", {})
        assert "bins" in requires
        assert "python3" in requires["bins"]
        assert "git" in requires["bins"]

    def test_extracts_requires_config(self, valid_frontmatter: str):
        """requires.config list is extracted correctly."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        result = SkillMarkdownParser.parse(valid_frontmatter)
        requires = result.get("requires", {})
        assert "config" in requires
        assert "log_level" in requires["config"]

    def test_missing_requires_section(self, minimal_frontmatter: str):
        """Skill without requires section returns empty dicts for requires."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        result = SkillMarkdownParser.parse(minimal_frontmatter)
        requires = result.get("requires", {})
        assert isinstance(requires, dict)


# ---------------------------------------------------------------------------
# Tests — primaryEnv, always, os Filtering
# ---------------------------------------------------------------------------

class TestSkillFilteringFields:
    """Test primaryEnv, always, and os filtering fields."""

    def test_extracts_primary_env(self, valid_frontmatter: str):
        """primaryEnv is extracted correctly."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        result = SkillMarkdownParser.parse(valid_frontmatter)
        assert result.get("primaryEnv") == "python3"

    def test_extracts_always_flag(self, valid_frontmatter: str):
        """always flag is extracted (default False when missing)."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        result = SkillMarkdownParser.parse(valid_frontmatter)
        assert result.get("always") is False

    def test_extracts_os_list(self, valid_frontmatter: str):
        """os list is extracted correctly."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        result = SkillMarkdownParser.parse(valid_frontmatter)
        os_list = result.get("os", [])
        assert "linux" in os_list
        assert "darwin" in os_list


# ---------------------------------------------------------------------------
# Tests — user-invocable, disable-model-invocation
# ---------------------------------------------------------------------------

class TestInvocationFlags:
    """Test user-invocable and disable-model-invocation flags."""

    def test_user_invokable_true(self, valid_frontmatter: str):
        """user-invocable is True in sample."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        result = SkillMarkdownParser.parse(valid_frontmatter)
        assert result.get("user-invocable") is True

    def test_disable_model_invocation_false(self, valid_frontmatter: str):
        """disable-model-invocation is False in sample."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        result = SkillMarkdownParser.parse(valid_frontmatter)
        assert result.get("disable-model-invocation") is False

    def test_flags_default_when_missing(self, minimal_frontmatter: str):
        """Flags default to sensible values when absent."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        result = SkillMarkdownParser.parse(minimal_frontmatter)
        # These should have sensible defaults, not raise KeyError
        assert result.get("user-invocable", False) in (True, False)
        assert result.get("disable-model-invocation", False) in (True, False)


# ---------------------------------------------------------------------------
# Tests — install Spec
# ---------------------------------------------------------------------------

class TestInstallSpec:
    """Test install spec extraction (brew/node/uv/download)."""

    def test_extracts_brew_packages(self, valid_frontmatter: str):
        """brew package list is extracted."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        result = SkillMarkdownParser.parse(valid_frontmatter)
        install = result.get("install", {})
        assert "brew" in install
        assert "wget" in install["brew"]
        assert "curl" in install["brew"]

    def test_extracts_node_packages(self, valid_frontmatter: str):
        """node package list is extracted."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        result = SkillMarkdownParser.parse(valid_frontmatter)
        install = result.get("install", {})
        assert "node" in install
        assert "typescript" in install["node"]

    def test_extracts_uv_packages(self, valid_frontmatter: str):
        """uv package list is extracted."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        result = SkillMarkdownParser.parse(valid_frontmatter)
        install = result.get("install", {})
        assert "uv" in install
        assert "requests" in install["uv"]

    def test_extracts_download_entries(self, valid_frontmatter: str):
        """download entries are extracted as list of dicts."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        result = SkillMarkdownParser.parse(valid_frontmatter)
        install = result.get("install", {})
        assert "download" in install
        downloads = install["download"]
        assert isinstance(downloads, list)
        assert len(downloads) == 1
        assert downloads[0].get("url") == "https://example.com/tool.tar.gz"


# ---------------------------------------------------------------------------
# Tests — wanclaw Extension Metadata
# ---------------------------------------------------------------------------

class TestWanClawExtension:
    """Test wanclaw extension metadata extraction."""

    def test_extracts_wanclaw_tools(self, valid_frontmatter: str):
        """wanclaw.tools list is extracted."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        result = SkillMarkdownParser.parse(valid_frontmatter)
        wanclaw = result.get("wanclaw", {})
        assert "tools" in wanclaw
        assert "bash" in wanclaw["tools"]
        assert "write" in wanclaw["tools"]

    def test_extracts_wanclaw_sandbox_policy(self, valid_frontmatter: str):
        """wanclaw.sandbox allowed/denied lists are extracted."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        result = SkillMarkdownParser.parse(valid_frontmatter)
        wanclaw = result.get("wanclaw", {})
        sandbox = wanclaw.get("sandbox", {})
        assert "allowed" in sandbox
        assert "denied" in sandbox
        assert "bash" in sandbox["allowed"]
        assert "delete" in sandbox["denied"]

    def test_extracts_wanclaw_max_tokens(self, valid_frontmatter: str):
        """wanclaw.maxTokens is extracted as int."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        result = SkillMarkdownParser.parse(valid_frontmatter)
        wanclaw = result.get("wanclaw", {})
        assert wanclaw.get("maxTokens") == 16000

    def test_extracts_wanclaw_max_skills_in_prompt(self, valid_frontmatter: str):
        """wanclaw.maxSkillsInPrompt is extracted."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        result = SkillMarkdownParser.parse(valid_frontmatter)
        wanclaw = result.get("wanclaw", {})
        assert wanclaw.get("maxSkillsInPrompt") == 3

    def test_extracts_wanclaw_max_skill_file_bytes(self, valid_frontmatter: str):
        """wanclaw.maxSkillFileBytes is extracted."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        result = SkillMarkdownParser.parse(valid_frontmatter)
        wanclaw = result.get("wanclaw", {})
        assert wanclaw.get("maxSkillFileBytes") == 20000

    def test_extracts_wanclaw_compact_format(self, valid_frontmatter: str):
        """wanclaw.compactFormat is extracted as bool."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        result = SkillMarkdownParser.parse(valid_frontmatter)
        wanclaw = result.get("wanclaw", {})
        assert wanclaw.get("compactFormat") is True


# ---------------------------------------------------------------------------
# Tests — Error Handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Test error handling for malformed frontmatter."""

    def test_malformed_yaml_raises_error(self, malformed_yaml_frontmatter: str):
        """Malformed YAML in frontmatter raises ValueError or yaml.YAMLError."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        with pytest.raises((ValueError, yaml.YAMLError)):
            SkillMarkdownParser.parse(malformed_yaml_frontmatter)

    def test_missing_closing_delimiter(self, missing_frontmatter_delimiter: str):
        """Missing closing --- delimiter raises ValueError."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        with pytest.raises(ValueError):
            SkillMarkdownParser.parse(missing_frontmatter_delimiter)

    def test_no_frontmatter_returns_raw(self, empty_frontmatter: str):
        """Document without frontmatter returns raw markdown as body."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        result = SkillMarkdownParser.parse(empty_frontmatter)
        # Should not raise; body/markdown should contain the text
        body = result.get("body") or result.get("markdown") or result.get("content", "")
        assert "# No Frontmatter" in body or "No Frontmatter" in body

    def test_empty_content_handled(self):
        """Empty string content is handled gracefully."""
        from wanclaw.agent.skill_md_parser import SkillMarkdownParser

        result = SkillMarkdownParser.parse("")
        assert isinstance(result, dict)
