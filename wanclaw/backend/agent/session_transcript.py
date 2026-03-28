"""
SessionTranscript — JSONL-based conversation transcript.

Provides crash-safe append, retrieval with limits, compaction,
and session-key routing for WanClaw agents.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class SessionTranscript:
    """
    JSONL-based transcript for a single session.

    File format: one JSON object per line.
    Each entry has: role, content, timestamp, session (optional).
    Tool entries also have: tool_name.

    Crash-safe: incomplete lines are skipped on read.
    """

    def __init__(
        self,
        path: Path | str,
        session_key: Optional[str] = None,
    ):
        self.path = Path(path)
        self.session_key = session_key
        self._ensure_parent_dir()

    def _ensure_parent_dir(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def append(
        self,
        role: str,
        content: str,
        tool_name: Optional[str] = None,
        **extra: Any,
    ) -> None:
        """Append a single entry to the transcript file."""
        entry: Dict[str, Any] = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if self.session_key:
            entry["session"] = self.session_key
        if tool_name:
            entry["tool_name"] = tool_name
        entry.update(extra)

        prefix = ""
        if self.path.exists():
            existing = self.path.read_text(encoding="utf-8")
            if existing and not existing.endswith("\n"):
                prefix = "\n"

        line = prefix + json.dumps(entry, ensure_ascii=False) + "\n"
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line)

    async def get_entries(
        self,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Return transcript entries, optionally limited to last N lines."""
        if not self.path.exists():
            return []

        entries: List[Dict[str, Any]] = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    entries.append(entry)
                except json.JSONDecodeError:
                    pass

        if self.session_key:
            entries = [e for e in entries if e.get("session") == self.session_key]

        if limit is not None:
            entries = entries[-limit:]

        return entries

    async def compact(self, keep: int) -> None:
        """Keep only the last N entries, rewrite the file."""
        entries = await self.get_entries()
        if keep <= 0:
            entries = []
        else:
            entries = entries[-keep:]

        lines = [json.dumps(e, ensure_ascii=False) + "\n" for e in entries]
        self.path.write_text("".join(lines), encoding="utf-8")

    async def search(self, keyword: str) -> List[Dict[str, Any]]:
        """Return entries containing keyword in content."""
        entries = await self.get_entries()
        return [
            e for e in entries
            if keyword.lower() in e.get("content", "").lower()
        ]
