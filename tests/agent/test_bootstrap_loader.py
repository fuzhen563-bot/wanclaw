"""
Tests for BootstrapLoader.

Validates ordered loading: SOUL → IDENTITY → USER → MEMORY → HEARTBEAT,
session key filtering, token budget enforcement, HEARTBEAT trigger filtering,
missing file handling, and bootstrap hooks override.
"""
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def workspace_with_all(tmp_path):
    """Workspace with all bootstrap files present."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    files = {
        "SOUL.md": "You are a helpful AI.",
        "IDENTITY.md": "Name: TestBot\nVersion: 1.0",
        "USER.md": "User: Alice",
        "MEMORY.md": "# Memory\n- fact: Alice likes coffee",
        "HEARTBEAT.md": "cron: */5 * * * *\nmessage: alive",
    }
    for name, content in files.items():
        (ws / name).write_text(content)
    return ws


@pytest.fixture
def workspace_partial(tmp_path):
    """Workspace with only some bootstrap files."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "SOUL.md").write_text("You are a bot.")
    (ws / "IDENTITY.md").write_text("Name: PartialBot")
    # USER.md, MEMORY.md, HEARTBEAT.md intentionally absent
    return ws


# ---------------------------------------------------------------------------
# Tests — Ordered Loading
# ---------------------------------------------------------------------------

class TestBootstrapLoaderOrder:
    """Bootstrap files must be loaded in the correct priority order."""

    def test_loads_soul_before_identity(self, workspace_with_all):
        """SOUL.md loads before IDENTITY.md."""
        from wanclaw.agent.bootstrap_loader import BootstrapLoader

        loader = BootstrapLoader(workspace_with_all)
        entries = loader.load_all()

        names = [e.get("source") or e.get("file") for e in entries]
        soul_idx = names.index("SOUL.md") if "SOUL.md" in names else -1
        identity_idx = names.index("IDENTITY.md") if "IDENTITY.md" in names else -1
        assert soul_idx < identity_idx, "SOUL.md must load before IDENTITY.md"

    def test_loads_identity_before_user(self, workspace_with_all):
        """IDENTITY.md loads before USER.md."""
        from wanclaw.agent.bootstrap_loader import BootstrapLoader

        loader = BootstrapLoader(workspace_with_all)
        entries = loader.load_all()

        names = [e.get("source") or e.get("file") for e in entries]
        identity_idx = names.index("IDENTITY.md") if "IDENTITY.md" in names else -1
        user_idx = names.index("USER.md") if "USER.md" in names else -1
        assert identity_idx < user_idx, "IDENTITY.md must load before USER.md"

    def test_loads_user_before_memory(self, workspace_with_all):
        """USER.md loads before MEMORY.md."""
        from wanclaw.agent.bootstrap_loader import BootstrapLoader

        loader = BootstrapLoader(workspace_with_all)
        entries = loader.load_all()

        names = [e.get("source") or e.get("file") for e in entries]
        user_idx = names.index("USER.md") if "USER.md" in names else -1
        memory_idx = names.index("MEMORY.md") if "MEMORY.md" in names else -1
        assert user_idx < memory_idx, "USER.md must load before MEMORY.md"

    def test_loads_memory_before_heartbeat(self, workspace_with_all):
        """MEMORY.md loads before HEARTBEAT.md."""
        from wanclaw.agent.bootstrap_loader import BootstrapLoader

        loader = BootstrapLoader(workspace_with_all)
        entries = loader.load_all()

        names = [e.get("source") or e.get("file") for e in entries]
        memory_idx = names.index("MEMORY.md") if "MEMORY.md" in names else -1
        heartbeat_idx = names.index("HEARTBEAT.md") if "HEARTBEAT.md" in names else -1
        assert memory_idx < heartbeat_idx, "MEMORY.md must load before HEARTBEAT.md"

    def test_all_five_bootstrap_types_loaded(self, workspace_with_all):
        """All five bootstrap file types appear in load_all()."""
        from wanclaw.agent.bootstrap_loader import BootstrapLoader

        loader = BootstrapLoader(workspace_with_all)
        entries = loader.load_all()

        sources = {e.get("source") or e.get("file") for e in entries}
        assert "SOUL.md" in sources
        assert "IDENTITY.md" in sources
        assert "USER.md" in sources
        assert "MEMORY.md" in sources
        assert "HEARTBEAT.md" in sources


# ---------------------------------------------------------------------------
# Tests — Session Key Filtering
# ---------------------------------------------------------------------------

class TestSessionKeyFiltering:
    """Per-session variant files (e.g., USER@channel.md) are filtered correctly."""

    def test_filters_per_session_variants(self, tmp_path):
        """Files with @session_key suffix are only loaded for matching session."""
        ws = tmp_path / "workspace"
        ws.mkdir()
        (ws / "SOUL.md").write_text("Base soul")
        (ws / "USER.md").write_text("Base user")
        (ws / "USER@agent:main:dm:alice.md").write_text("Alice-specific user")

        from wanclaw.agent.bootstrap_loader import BootstrapLoader

        # Loading for alice session should include the per-session variant
        loader_alice = BootstrapLoader(ws)
        entries_alice = loader_alice.load_all(session_key="agent:main:dm:alice")
        sources_alice = [e.get("source") or e.get("file") for e in entries_alice]
        assert "USER@agent:main:dm:alice.md" in sources_alice

        # Loading for bob session should NOT include alice variant
        loader_bob = BootstrapLoader(ws)
        entries_bob = loader_bob.load_all(session_key="agent:main:dm:bob")
        sources_bob = [e.get("source") or e.get("file") for e in entries_bob]
        assert "USER@agent:main:dm:alice.md" not in sources_bob

    def test_base_file_always_loaded(self, tmp_path):
        """Base files (without @ suffix) are always loaded regardless of session."""
        ws = tmp_path / "workspace"
        ws.mkdir()
        (ws / "SOUL.md").write_text("Base soul")
        (ws / "USER@session1.md").write_text("Session1 user")

        from wanclaw.agent.bootstrap_loader import BootstrapLoader

        loader = BootstrapLoader(ws)
        entries = loader.load_all(session_key="session2")
        sources = [e.get("source") or e.get("file") for e in entries]
        assert "SOUL.md" in sources
        assert "USER@session1.md" not in sources


# ---------------------------------------------------------------------------
# Tests — Token Budget Enforcement
# ---------------------------------------------------------------------------

class TestTokenBudgetEnforcement:
    """Total bootstrap content must respect token budget."""

    def test_respects_max_token_budget(self, tmp_path):
        """load_all() with max_tokens limits total output."""
        ws = tmp_path / "workspace"
        ws.mkdir()
        (ws / "SOUL.md").write_text("A" * 1000)
        (ws / "IDENTITY.md").write_text("B" * 1000)

        from wanclaw.agent.bootstrap_loader import BootstrapLoader

        loader = BootstrapLoader(ws)
        # max_tokens=500 should cause truncation
        entries = loader.load_all(max_tokens=500)
        total = sum(len(e.get("content", "")) for e in entries)
        # Should be roughly within budget (exact tolerance depends on tokenizer)
        assert total <= 600, "Total content should be within token budget"

    def test_truncation_indicator_present(self, tmp_path):
        """When content is truncated, entries include a truncation flag."""
        ws = tmp_path / "workspace"
        ws.mkdir()
        (ws / "SOUL.md").write_text("X" * 5000)

        from wanclaw.agent.bootstrap_loader import BootstrapLoader

        loader = BootstrapLoader(ws)
        entries = loader.load_all(max_tokens=100)
        # At least one entry should be marked as truncated
        truncated = [e for e in entries if e.get("truncated") or e.get("_truncated")]
        assert len(truncated) > 0, "Truncated entries should be flagged"

    def test_high_budget_includes_all(self, tmp_path):
        """High token budget includes all content without truncation."""
        ws = tmp_path / "workspace"
        ws.mkdir()
        (ws / "SOUL.md").write_text("Y" * 500)
        (ws / "IDENTITY.md").write_text("Z" * 500)

        from wanclaw.agent.bootstrap_loader import BootstrapLoader

        loader = BootstrapLoader(ws)
        entries = loader.load_all(max_tokens=100000)
        # None should be truncated with generous budget
        truncated = [e for e in entries if e.get("truncated") or e.get("_truncated")]
        assert len(truncated) == 0, "No truncation with generous budget"


# ---------------------------------------------------------------------------
# Tests — HEARTBEAT Trigger Filtering
# ---------------------------------------------------------------------------

class TestHeartbeatFiltering:
    """HEARTBEAT.md is only loaded for cron/heartbeat triggers."""

    def test_heartbeat_not_loaded_for_regular_session(self, workspace_with_all):
        """HEARTBEAT.md excluded from normal load_all()."""
        from wanclaw.agent.bootstrap_loader import BootstrapLoader

        loader = BootstrapLoader(workspace_with_all)
        entries = loader.load_all(trigger="message")
        sources = {e.get("source") or e.get("file") for e in entries}
        assert "HEARTBEAT.md" not in sources

    def test_heartbeat_loaded_for_cron_trigger(self, workspace_with_all):
        """HEARTBEAT.md included when trigger is 'cron'."""
        from wanclaw.agent.bootstrap_loader import BootstrapLoader

        loader = BootstrapLoader(workspace_with_all)
        entries = loader.load_all(trigger="cron")
        sources = {e.get("source") or e.get("file") for e in entries}
        assert "HEARTBEAT.md" in sources

    def test_heartbeat_loaded_for_heartbeat_trigger(self, workspace_with_all):
        """HEARTBEAT.md included when trigger is 'heartbeat'."""
        from wanclaw.agent.bootstrap_loader import BootstrapLoader

        loader = BootstrapLoader(workspace_with_all)
        entries = loader.load_all(trigger="heartbeat")
        sources = {e.get("source") or e.get("file") for e in entries}
        assert "HEARTBEAT.md" in sources


# ---------------------------------------------------------------------------
# Tests — Missing Files Handled Gracefully
# ---------------------------------------------------------------------------

class TestMissingFiles:
    """Missing bootstrap files are handled without error."""

    def test_partial_workspace_no_error(self, workspace_partial):
        """Loading workspace with missing files does not raise."""
        from wanclaw.agent.bootstrap_loader import BootstrapLoader

        loader = BootstrapLoader(workspace_partial)
        # Should not raise FileNotFoundError
        entries = loader.load_all()
        assert isinstance(entries, list)

    def test_missing_user_handled(self, tmp_path):
        """Missing USER.md does not raise."""
        ws = tmp_path / "workspace"
        ws.mkdir()
        (ws / "SOUL.md").write_text("Soul only")
        # USER.md, MEMORY.md, HEARTBEAT.md missing

        from wanclaw.agent.bootstrap_loader import BootstrapLoader

        loader = BootstrapLoader(ws)
        entries = loader.load_all()
        assert isinstance(entries, list)
        sources = {e.get("source") or e.get("file") for e in entries}
        assert "USER.md" not in sources

    def test_empty_workspace_no_error(self, tmp_path):
        """Empty workspace directory is handled gracefully."""
        ws = tmp_path / "workspace"
        ws.mkdir()
        # No files at all

        from wanclaw.agent.bootstrap_loader import BootstrapLoader

        loader = BootstrapLoader(ws)
        entries = loader.load_all()
        assert entries == [] or entries == {} or entries is not None


# ---------------------------------------------------------------------------
# Tests — Bootstrap Hooks Override
# ---------------------------------------------------------------------------

class TestBootstrapHooks:
    """Bootstrap hooks can override default content."""

    def test_hook_can_override_soul(self, tmp_path):
        """A hook function can replace SOUL.md content."""
        ws = tmp_path / "workspace"
        ws.mkdir()
        (ws / "SOUL.md").write_text("Original soul")

        from wanclaw.agent.bootstrap_loader import BootstrapLoader

        def override_soul(entry: dict) -> dict:
            entry["content"] = "Overridden soul by hook"
            return entry

        loader = BootstrapLoader(ws)
        entries = loader.load_all(hooks={"SOUL.md": override_soul})
        soul_entry = next(
            (e for e in entries if (e.get("source") or e.get("file")) == "SOUL.md"),
            None,
        )
        assert soul_entry is not None
        assert soul_entry.get("content") == "Overridden soul by hook"

    def test_hook_receives_entry_dict(self, tmp_path):
        """Hook receives and can modify the entry dict."""
        ws = tmp_path / "workspace"
        ws.mkdir()
        (ws / "IDENTITY.md").write_text("Original identity")

        from wanclaw.agent.bootstrap_loader import BootstrapLoader

        received = {}

        def capture_hook(entry: dict) -> dict:
            received.update(entry)
            return entry

        loader = BootstrapLoader(ws)
        loader.load_all(hooks={"IDENTITY.md": capture_hook})
        assert "content" in received or "source" in received

    def test_hook_for_missing_file_not_called(self, tmp_path):
        """Hooks for absent files are not invoked."""
        ws = tmp_path / "workspace"
        ws.mkdir()
        (ws / "SOUL.md").write_text("Soul")

        from wanclaw.agent.bootstrap_loader import BootstrapLoader

        call_count = 0

        def count_hook(entry: dict) -> dict:
            nonlocal call_count
            call_count += 1
            return entry

        loader = BootstrapLoader(ws)
        loader.load_all(hooks={"USER.md": count_hook})
        assert call_count == 0, "Hook for missing file should not be called"
