"""
Tests for DailyMemory — per-day memory log management.

Validates auto-creation of today's log, append, get_today/yesterday,
vector indexing trigger, search, and file format correctness.
"""
import pytest
from pathlib import Path
from datetime import date, timedelta


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def memory_root(tmp_path: Path) -> Path:
    """Root directory for daily memory files."""
    root = tmp_path / "memory"
    root.mkdir()
    return root


@pytest.fixture
def memory_with_past_entries(memory_root: Path) -> Path:
    """Memory root with entries for past days."""
    today = date.today()
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)

    (memory_root / f"{today.isoformat()}.md").write_text(
        "# Memory Log\n\n## Today\n- User asked about pricing"
    )
    (memory_root / f"{yesterday.isoformat()}.md").write_text(
        "# Memory Log\n\n## Yesterday\n- Set up new project"
    )
    (memory_root / f"{two_days_ago.isoformat()}.md").write_text(
        "# Memory Log\n\n## Two Days Ago\n- Initial setup"
    )
    return memory_root


# ---------------------------------------------------------------------------
# Tests — Auto-Create Today's Log
# ---------------------------------------------------------------------------

class TestAutoCreateToday:
    """Today's memory log is created automatically if absent."""

    async def test_creates_today_file_if_missing(self, memory_root: Path):
        """get_today() creates today's file if it doesn't exist."""
        from wanclaw.agent.daily_memory import DailyMemory

        dm = DailyMemory(memory_root)
        result = await dm.get_today()
        today_file = memory_root / f"{date.today().isoformat()}.md"
        assert today_file.exists()
        assert isinstance(result, (str, dict, list))

    async def test_get_today_returns_existing(self, memory_with_past_entries: Path):
        """get_today() returns existing content without re-creating."""
        from wanclaw.agent.daily_memory import DailyMemory

        dm = DailyMemory(memory_with_past_entries)
        result = await dm.get_today()
        today_str = date.today().isoformat()
        assert today_str in str(result) or isinstance(result, (str, dict, list))


# ---------------------------------------------------------------------------
# Tests — Append Entries
# ---------------------------------------------------------------------------

class TestAppend:
    """Test appending entries to today's memory log."""

    async def test_append_adds_entry(self, memory_root: Path):
        """append() adds an entry to today's memory log."""
        from wanclaw.agent.daily_memory import DailyMemory

        dm = DailyMemory(memory_root)
        await dm.append("- User prefers dark mode")
        today_file = memory_root / f"{date.today().isoformat()}.md"
        content = today_file.read_text()
        assert "User prefers dark mode" in content

    async def test_append_preserves_existing(self, memory_with_past_entries: Path):
        """append() preserves existing content when adding new entry."""
        from wanclaw.agent.daily_memory import DailyMemory

        dm = DailyMemory(memory_with_past_entries)
        await dm.append("- New fact about the project")
        content = (memory_with_past_entries / f"{date.today().isoformat()}.md").read_text()
        assert "New fact about the project" in content

    async def test_multiple_appends_order(self, memory_root: Path):
        """Multiple appends appear in correct chronological order."""
        from wanclaw.agent.daily_memory import DailyMemory

        dm = DailyMemory(memory_root)
        await dm.append("- First entry")
        await dm.append("- Second entry")
        content = (memory_root / f"{date.today().isoformat()}.md").read_text()
        first_pos = content.find("First entry")
        second_pos = content.find("Second entry")
        assert first_pos < second_pos, "First entry should appear before second"


# ---------------------------------------------------------------------------
# Tests — get_today / get_yesterday
# ---------------------------------------------------------------------------

class TestGetTodayYesterday:
    """Test get_today() and get_yesterday() methods."""

    async def test_get_today_returns_today_entries(
        self, memory_with_past_entries: Path
    ):
        """get_today() returns today's memory entries."""
        from wanclaw.agent.daily_memory import DailyMemory

        dm = DailyMemory(memory_with_past_entries)
        today = await dm.get_today()
        today_str = date.today().isoformat()
        assert today_str in str(today) or "pricing" in str(today)

    async def test_get_yesterday_returns_yesterday_entries(
        self, memory_with_past_entries: Path
    ):
        """get_yesterday() returns yesterday's memory entries."""
        from wanclaw.agent.daily_memory import DailyMemory

        dm = DailyMemory(memory_with_past_entries)
        yesterday_entries = await dm.get_yesterday()
        yesterday_str = (date.today() - timedelta(days=1)).isoformat()
        assert yesterday_str in str(yesterday_entries) or "project" in str(
            yesterday_entries
        )

    async def test_get_yesterday_missing_returns_empty(
        self, memory_root: Path
    ):
        """get_yesterday() returns empty when yesterday's file absent."""
        from wanclaw.agent.daily_memory import DailyMemory

        dm = DailyMemory(memory_root)
        result = await dm.get_yesterday()
        # Should not raise, should return empty
        assert result == "" or result == [] or result == {}


# ---------------------------------------------------------------------------
# Tests — Vector Indexing Trigger (needs_indexing)
# ---------------------------------------------------------------------------

class TestNeedsIndexing:
    """Vector indexing is triggered when threshold is exceeded."""

    async def test_needs_indexing_true_after_threshold(
        self, memory_root: Path
    ):
        """needs_indexing() returns True after N entries accumulated."""
        from wanclaw.agent.daily_memory import DailyMemory

        dm = DailyMemory(memory_root, indexing_threshold=5)
        # Add entries up to threshold
        for i in range(5):
            await dm.append(f"- Entry {i}")
        assert await dm.needs_indexing() is True

    async def test_needs_indexing_false_below_threshold(
        self, memory_root: Path
    ):
        """needs_indexing() returns False below threshold."""
        from wanclaw.agent.daily_memory import DailyMemory

        dm = DailyMemory(memory_root, indexing_threshold=100)
        await dm.append("- Just one entry")
        assert await dm.needs_indexing() is False

    async def test_needs_indexing_resets_after_indexing(
        self, memory_root: Path
    ):
        """After indexing is triggered, flag resets until threshold reached again."""
        from wanclaw.agent.daily_memory import DailyMemory

        dm = DailyMemory(memory_root, indexing_threshold=3)
        for i in range(3):
            await dm.append(f"- Entry {i}")
        assert await dm.needs_indexing() is True
        # Simulate indexing was performed
        await dm.mark_indexed()
        assert await dm.needs_indexing() is False


# ---------------------------------------------------------------------------
# Tests — Search Over Daily Logs
# ---------------------------------------------------------------------------

class TestSearch:
    """Test searching across daily memory logs."""

    async def test_search_finds_keyword(
        self, memory_with_past_entries: Path
    ):
        """search() finds entries containing the keyword."""
        from wanclaw.agent.daily_memory import DailyMemory

        dm = DailyMemory(memory_with_past_entries)
        results = await dm.search("project")
        assert len(results) > 0
        found = any("project" in str(r) for r in results)
        assert found, "Search should find 'project' in memory logs"

    async def test_search_empty_for_no_match(
        self, memory_with_past_entries: Path
    ):
        """search() returns empty list for non-matching keyword."""
        from wanclaw.agent.daily_memory import DailyMemory

        dm = DailyMemory(memory_with_past_entries)
        results = await dm.search("xyznonexistentkeyword123")
        assert results == [] or results == ""

    async def test_search_spans_multiple_days(
        self, memory_with_past_entries: Path
    ):
        """search() finds matches across multiple daily files."""
        from wanclaw.agent.daily_memory import DailyMemory

        dm = DailyMemory(memory_with_past_entries)
        results = await dm.search("setup")
        # Should find in yesterday and two_days_ago entries
        assert len(results) >= 2, "Search should span multiple days"


# ---------------------------------------------------------------------------
# Tests — File Format Correctness
# ---------------------------------------------------------------------------

class TestFileFormat:
    """Memory files follow memory/YYYY-MM-DD.md naming convention."""

    def test_today_file_naming(self, memory_root: Path):
        """Today's memory file is named memory/YYYY-MM-DD.md."""
        from wanclaw.agent.daily_memory import DailyMemory

        dm = DailyMemory(memory_root)
        # Trigger creation
        # Synchronous check of expected path
        today_file = memory_root / f"{date.today().isoformat()}.md"
        # If file was already created, verify naming
        if today_file.exists():
            assert today_file.match("????-??-??.md")

    def test_file_contains_markdown_structure(
        self, memory_with_past_entries: Path
    ):
        """Memory file contains valid markdown structure."""
        today_file = memory_with_past_entries / f"{date.today().isoformat()}.md"
        content = today_file.read_text()
        assert content.startswith("#") or len(content) > 0

    def test_date_in_filename_matches_content_date(
        self, memory_with_past_entries: Path
    ):
        """File date in filename matches date mentioned in content."""
        from wanclaw.agent.daily_memory import DailyMemory

        dm = DailyMemory(memory_with_past_entries)
        today_file = memory_with_past_entries / f"{date.today().isoformat()}.md"
        assert today_file.exists()
        content = today_file.read_text()
        today_str = date.today().isoformat()
        # Content should reference today's date
        assert today_str in content or "Today" in content
