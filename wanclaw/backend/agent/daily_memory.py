"""
DailyMemory — per-day memory log management.

Memory logs are stored as memory/YYYY-MM-DD.md files.
Provides auto-creation, append, search, and vector indexing triggers.
"""
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

logger = logging.getLogger(__name__)


class DailyMemory:
    """
    Manages daily memory log files under a root directory.

    File naming: YYYY-MM-DD.md (e.g., 2025-03-28.md)
    Auto-creates today's file on first access.
    Triggers vector indexing when entry count exceeds threshold.
    """

    HEADER_TEMPLATE = "# Memory Log\n\n## Today\n"

    def __init__(
        self,
        root: Path | str,
        indexing_threshold: int = 50,
    ):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.indexing_threshold = indexing_threshold
        self._indexed: bool = False

    def _today_path(self) -> Path:
        return self.root / f"{date.today().isoformat()}.md"

    def _date_path(self, d: date) -> Path:
        return self.root / f"{d.isoformat()}.md"

    async def get_today(self) -> Union[str, List, Dict]:
        """Return today's memory content, creating file if absent."""
        path = self._today_path()
        if not path.exists():
            path.write_text(self.HEADER_TEMPLATE, encoding="utf-8")
        return path.read_text(encoding="utf-8")

    async def get_yesterday(self) -> Union[str, List, Dict]:
        """Return yesterday's memory content, or empty if absent."""
        yesterday = date.today() - timedelta(days=1)
        path = self._date_path(yesterday)
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    async def append(self, entry: str) -> None:
        """Append an entry to today's memory log."""
        path = self._today_path()
        if not path.exists():
            path.write_text(self.HEADER_TEMPLATE, encoding="utf-8")

        content = path.read_text(encoding="utf-8")
        content += entry + "\n"
        path.write_text(content, encoding="utf-8")
        self._indexed = False

    async def needs_indexing(self) -> bool:
        """Return True if entry count exceeds threshold and not yet indexed."""
        if self._indexed:
            return False
        path = self._today_path()
        if not path.exists():
            return False
        lines = path.read_text(encoding="utf-8").splitlines()
        entry_lines = [
            l for l in lines
            if l.strip() and not l.strip().startswith("#")
        ]
        return len(entry_lines) >= self.indexing_threshold

    async def mark_indexed(self) -> None:
        """Reset indexing flag after vector indexing completes."""
        self._indexed = True

    async def search(
        self,
        keyword: str,
        days_back: int = 30,
    ) -> List[Dict[str, Any]]:
        """Search across recent daily memory files for keyword."""
        results: List[Dict[str, Any]] = []
        today = date.today()
        kw_normalized = keyword.lower().replace(" ", "")
        for i in range(days_back):
            d = today - timedelta(days=i)
            path = self._date_path(d)
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8")
            if kw_normalized in content.lower().replace(" ", ""):
                results.append({
                    "date": d.isoformat(),
                    "content": content,
                })
        return results
