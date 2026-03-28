"""
Tests for SessionTranscript — JSONL-based conversation transcript.

Validates append, get_entries with limit, crash-safe partial write,
compaction, session key routing, and JSONL format correctness.
"""
import json
import os
import pytest
from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def transcript_path(tmp_path: Path) -> Path:
    """Path to transcript JSONL file in temp dir."""
    return tmp_path / "transcripts" / "test_session.jsonl"


@pytest.fixture
def populated_transcript(
    tmp_path: Path, sample_transcript_entries: list[dict]
) -> tuple[Path, list[dict]]:
    """Transcript file pre-populated with sample entries."""
    transcript_dir = tmp_path / "transcripts"
    transcript_dir.mkdir(parents=True)
    path = transcript_dir / "populated.jsonl"

    with open(path, "w") as f:
        for entry in sample_transcript_entries:
            f.write(json.dumps(entry) + "\n")

    return path, sample_transcript_entries


# ---------------------------------------------------------------------------
# Tests — Append
# ---------------------------------------------------------------------------

class TestAppend:
    """Test appending entries to transcript."""

    async def test_append_user_role(self, transcript_path: Path):
        """Appending user role entry succeeds."""
        from wanclaw.agent.session_transcript import SessionTranscript

        transcript = SessionTranscript(transcript_path)
        await transcript.append(role="user", content="Hello")
        assert transcript_path.exists()

    async def test_append_assistant_role(self, transcript_path: Path):
        """Appending assistant role entry succeeds."""
        from wanclaw.agent.session_transcript import SessionTranscript

        transcript = SessionTranscript(transcript_path)
        await transcript.append(role="assistant", content="Hi there!")
        assert transcript_path.exists()

    async def test_append_tool_role(self, transcript_path: Path):
        """Appending tool role entry with tool_name succeeds."""
        from wanclaw.agent.session_transcript import SessionTranscript

        transcript = SessionTranscript(transcript_path)
        await transcript.append(
            role="tool", content="Tool output", tool_name="bash"
        )
        assert transcript_path.exists()

    async def test_append_includes_timestamp(self, transcript_path: Path):
        """Appended entries include a timestamp field."""
        from wanclaw.agent.session_transcript import SessionTranscript

        transcript = SessionTranscript(transcript_path)
        await transcript.append(role="user", content="Test")
        entries = await transcript.get_entries()
        assert len(entries) == 1
        assert "timestamp" in entries[0]
        assert entries[0]["timestamp"] != ""

    async def test_append_includes_session_key(self, transcript_path: Path):
        """Appended entries include the session key."""
        from wanclaw.agent.session_transcript import SessionTranscript

        transcript = SessionTranscript(
            transcript_path, session_key="agent:main:test"
        )
        await transcript.append(role="user", content="Test")
        entries = await transcript.get_entries()
        assert entries[0].get("session") == "agent:main:test"


# ---------------------------------------------------------------------------
# Tests — get_entries with Limit
# ---------------------------------------------------------------------------

class TestGetEntries:
    """Test retrieving entries with and without limits."""

    async def test_get_all_entries(
        self, populated_transcript: tuple[Path, list[dict]]
    ):
        """get_entries() without limit returns all entries."""
        from wanclaw.agent.session_transcript import SessionTranscript

        path, expected = populated_transcript
        transcript = SessionTranscript(path)
        entries = await transcript.get_entries()
        assert len(entries) == len(expected)

    async def test_get_entries_with_limit(
        self, populated_transcript: tuple[Path, list[dict]]
    ):
        """get_entries(limit=N) returns last N entries."""
        from wanclaw.agent.session_transcript import SessionTranscript

        path, expected = populated_transcript
        transcript = SessionTranscript(path)
        entries = await transcript.get_entries(limit=2)
        assert len(entries) == 2

    async def test_get_entries_returns_chronological_order(
        self, populated_transcript: tuple[Path, list[dict]]
    ):
        """Entries are returned in chronological order (oldest first)."""
        from wanclaw.agent.session_transcript import SessionTranscript

        path, expected = populated_transcript
        transcript = SessionTranscript(path)
        entries = await transcript.get_entries()
        timestamps = [e["timestamp"] for e in entries]
        assert timestamps == sorted(timestamps)

    async def test_get_entries_empty_for_new_file(self, transcript_path: Path):
        """get_entries() on empty/new transcript returns empty list."""
        from wanclaw.agent.session_transcript import SessionTranscript

        transcript = SessionTranscript(transcript_path)
        entries = await transcript.get_entries()
        assert entries == []


# ---------------------------------------------------------------------------
# Tests — Crash-Safe Partial Write
# ---------------------------------------------------------------------------

class TestCrashSafeWrite:
    """Partial writes are recovered gracefully after crashes."""

    async def test_incomplete_line_not_returned(self, tmp_path: Path):
        """A file ending with an incomplete JSON line is handled."""
        from wanclaw.agent.session_transcript import SessionTranscript

        path = tmp_path / "crash_test.jsonl"
        # Write a partial/corrupt line
        path.write_text("""{"role": "user", "content": "Hello"}
{"role": "ass""")

        transcript = SessionTranscript(path)
        entries = await transcript.get_entries()
        # Should return only the valid entry, not the partial one
        assert len(entries) == 1
        assert entries[0]["content"] == "Hello"

    async def test_append_after_corruption_recovery(self, tmp_path: Path):
        """Can append new entries after recovering from corruption."""
        from wanclaw.agent.session_transcript import SessionTranscript

        path = tmp_path / "recovery_test.jsonl"
        path.write_text('{"role": "user", "content": "A"}\n{"role": "ass')

        transcript = SessionTranscript(path)
        await transcript.append(role="user", content="B")
        entries = await transcript.get_entries()
        assert len(entries) == 2
        assert entries[1]["content"] == "B"

    async def test_empty_file_handled(self, tmp_path: Path):
        """Empty file (0 bytes) returns no entries."""
        from wanclaw.agent.session_transcript import SessionTranscript

        path = tmp_path / "empty.jsonl"
        path.write_text("")

        transcript = SessionTranscript(path)
        entries = await transcript.get_entries()
        assert entries == []


# ---------------------------------------------------------------------------
# Tests — Compaction (Keep Last N Entries)
# ---------------------------------------------------------------------------

class TestCompaction:
    """Compaction keeps only the last N entries."""

    async def test_compact_keeps_last_n(self, populated_transcript: tuple[Path, list]):
        """compact(keep=N) keeps only the last N entries."""
        from wanclaw.agent.session_transcript import SessionTranscript

        path, _ = populated_transcript
        transcript = SessionTranscript(path)
        await transcript.compact(keep=1)
        entries = await transcript.get_entries()
        assert len(entries) == 1

    async def test_compact_preserves_recent_entries(self, populated_transcript):
        """compact() keeps the most recent entries (by timestamp)."""
        from wanclaw.agent.session_transcript import SessionTranscript

        path, all_entries = populated_transcript
        transcript = SessionTranscript(path)
        await transcript.compact(keep=2)
        entries = await transcript.get_entries()
        assert len(entries) == 2
        # Most recent two entries kept
        assert entries[-1]["content"] == all_entries[-1]["content"]

    async def test_compact_zero_keeps_nothing(self, tmp_path: Path):
        """compact(keep=0) clears all entries."""
        from wanclaw.agent.session_transcript import SessionTranscript

        path = tmp_path / "zero_compact.jsonl"
        path.write_text(
            '{"role":"user","content":"A","timestamp":"2024-01-01T00:00:00Z"}\n'
        )
        transcript = SessionTranscript(path)
        await transcript.compact(keep=0)
        entries = await transcript.get_entries()
        assert entries == []


# ---------------------------------------------------------------------------
# Tests — Session Key Routing
# ---------------------------------------------------------------------------

class TestSessionRouting:
    """Entries are associated with session keys."""

    async def test_session_key_in_entry(self, transcript_path: Path):
        """Each entry carries the correct session key."""
        from wanclaw.agent.session_transcript import SessionTranscript

        transcript = SessionTranscript(
            transcript_path, session_key="agent:main:alice"
        )
        await transcript.append(role="user", content="Hi")
        entries = await transcript.get_entries()
        assert entries[0]["session"] == "agent:main:alice"

    async def test_different_session_keys_different_files(
        self, tmp_path: Path
    ):
        """Different session keys write to different files or filter correctly."""
        from wanclaw.agent.session_transcript import SessionTranscript

        path1 = tmp_path / "session_a.jsonl"
        path2 = tmp_path / "session_b.jsonl"

        t1 = SessionTranscript(path1, session_key="agent:main:a")
        t2 = SessionTranscript(path2, session_key="agent:main:b")

        await t1.append(role="user", content="From A")
        await t2.append(role="user", content="From B")

        entries1 = await t1.get_entries()
        entries2 = await t2.get_entries()

        assert entries1[0]["content"] == "From A"
        assert entries2[0]["content"] == "From B"


# ---------------------------------------------------------------------------
# Tests — JSONL Format Correctness
# ---------------------------------------------------------------------------

class TestJsonlFormat:
    """Each line in the transcript file is valid JSON."""

    async def test_all_lines_are_valid_json(self, populated_transcript: tuple[Path, list]):
        """Every line in the file parses as JSON."""
        path, _ = populated_transcript
        from wanclaw.agent.session_transcript import SessionTranscript

        transcript = SessionTranscript(path)
        entries = await transcript.get_entries()

        with open(path) as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    json.loads(line)
                except json.JSONDecodeError as e:
                    pytest.fail(f"Line {i} is not valid JSON: {e}")

    async def test_each_entry_has_required_fields(
        self, populated_transcript: tuple[Path, list]
    ):
        """Each entry has role and content fields."""
        from wanclaw.agent.session_transcript import SessionTranscript

        path, _ = populated_transcript
        transcript = SessionTranscript(path)
        entries = await transcript.get_entries()

        for entry in entries:
            assert "role" in entry
            assert "content" in entry

    async def test_tool_entries_have_tool_name(
        self, transcript_path: Path
    ):
        """Tool role entries include tool_name field."""
        from wanclaw.agent.session_transcript import SessionTranscript

        transcript = SessionTranscript(transcript_path)
        await transcript.append(role="tool", content="out", tool_name="bash")
        entries = await transcript.get_entries()

        tool_entries = [e for e in entries if e["role"] == "tool"]
        assert len(tool_entries) == 1
        assert tool_entries[0].get("tool_name") == "bash"
