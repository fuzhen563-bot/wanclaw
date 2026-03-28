"""
WanClaw Bootstrap File Loader

Loads OpenClaw-style bootstrap files for agent context:
- SOUL.md       → Core personality/values
- IDENTITY.md   → Agent identity
- USER.md       → User-specific context (account-scoped)
- MEMORY.md     → Curated long-term memory
- HEARTBEAT.md  → Cron-triggered autonomous tasks
- SKILLS.md     → Inline skill catalog (optional)

Load order (for context assembly):
  SOUL.md → IDENTITY.md → USER.md → MEMORY.md → SKILLS.md → HEARTBEAT.md
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class BootstrapOrder(Enum):
    """Bootstrap file load priority (lower = loaded first)."""
    SOUL = 1
    IDENTITY = 2
    USER = 3
    MEMORY = 4
    SKILLS = 5
    HEARTBEAT = 6


@dataclass
class BootstrapFile:
    name: str  # SOUL, IDENTITY, etc.
    path: str   # Full file path
    content: Optional[str] = None
    missing: bool = False
    file_path: Optional[str] = None  # Relative path for prompt


@dataclass
class BootstrapContext:
    """Loaded bootstrap context for a session."""
    files: List[BootstrapFile] = field(default_factory=list)
    total_chars: int = 0
    sections: List[str] = field(default_factory=list)  # ["SOUL", "IDENTITY", etc.]
    missing_files: List[str] = field(default_factory=list)


@dataclass
class BootstrapConfig:
    """Configuration for bootstrap loading."""
    bootstrap_max_chars: int = 20000  # Per-file limit
    bootstrap_total_max_chars: int = 50000  # Total limit
    warn_ratio: float = 0.80  # Warn when at 80% of limit
    hard_min_ratio: float = 0.90  # Critical when at 90%


class BootstrapLoader:
    """
    Loads and manages bootstrap files for agent context.

    Workspace layout:
      ~/.wanclaw/
        SOUL.md          # Global personality
        IDENTITY.md      # Global identity
        MEMORY.md        # Global curated memory
        SKILLS.md        # Inline skills
        agents/
          <agent_id>/
            SOUL.md      # Agent-specific overrides
            IDENTITY.md
            MEMORY.md
            HEARTBEAT.md
        accounts/
          <account_id>/
            USER.md       # Account-specific user context
    """

    BOOTSTRAP_FILES = {
        "SOUL": "SOUL.md",
        "IDENTITY": "IDENTITY.md",
        "USER": "USER.md",
        "MEMORY": "MEMORY.md",
        "SKILLS": "SKILLS.md",
        "HEARTBEAT": "HEARTBEAT.md",
    }

    def __init__(
        self,
        workspace_dir: str = "~/.wanclaw",
        agent_id: str = "main",
        account_id: Optional[str] = None,
        config: Optional[BootstrapConfig] = None,
    ):
        self.workspace_dir = os.path.expanduser(workspace_dir)
        self.agent_id = agent_id
        self.account_id = account_id
        self.config = config or BootstrapConfig()

    def resolve_path(self, filename: str) -> str:
        """Resolve the path for a bootstrap file.

        Priority:
        1. agent-specific path (~/.wanclaw/agents/<agent_id>/<filename>)
        2. account-scoped path (~/.wanclaw/accounts/<account_id>/<filename>) for USER.md
        3. global path (~/.wanclaw/<filename>)
        """
        # Agent-specific path takes precedence
        agent_path = os.path.join(
            self.workspace_dir, "agents", self.agent_id, filename
        )
        if os.path.exists(agent_path):
            return agent_path

        # Account-scoped path for USER.md
        if self.account_id and filename == "USER.md":
            account_path = os.path.join(
                self.workspace_dir, "accounts", self.account_id, filename
            )
            if os.path.exists(account_path):
                return account_path

        # Global path fallback
        global_path = os.path.join(self.workspace_dir, filename)
        return global_path

    def load_file(self, name: str) -> BootstrapFile:
        """Load a single bootstrap file by name."""
        filename = self.BOOTSTRAP_FILES.get(name, f"{name}.md")
        path = self.resolve_path(filename)
        missing = False
        content = ""

        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except (IOError, OSError) as e:
                logger.warning(f"Failed to read bootstrap file {path}: {e}")
                missing = True
        else:
            missing = True

        return BootstrapFile(
            name=name,
            path=path,
            content=content if not missing else None,
            missing=missing,
            file_path=filename,
        )

    def _load_all_candidates(self) -> List[BootstrapFile]:
        """Load all bootstrap files that exist, in order."""
        files: List[BootstrapFile] = []
        for name in BootstrapOrder:
            bf = self.load_file(name.name)
            files.append(bf)
        return files

    def _filter_by_trigger(
        self,
        files: List[BootstrapFile],
        trigger: str,
    ) -> tuple[List[BootstrapFile], bool]:
        """Filter files based on trigger type.

        Returns (filtered_files, heartbeat_included) tuple.
        HEARTBEAT always remains in the list (for ordering),
        but heartbeat_included=False means skip it when building entries.
        """
        heartbeat_included = trigger in ("heartbeat", "cron")
        return files, heartbeat_included

    def _filter_by_session(
        self,
        files: List[BootstrapFile],
        session_key: Optional[str],
        workspace_path: str,
    ) -> List[BootstrapFile]:
        """Filter files based on session characteristics.

        Rules:
        - USER.md always included from root workspace
        - Per-session variants (USER@key.md) included when session_key matches
        - Per-session variants take precedence over base USER.md
        """
        result: List[BootstrapFile] = []
        user_loaded = False

        for bf in files:
            if bf.name != "USER":
                result.append(bf)
                continue

            if session_key:
                variant_filename = f"USER@{session_key}.md"
                variant_path = os.path.join(workspace_path, variant_filename)
                if os.path.exists(variant_path):
                    try:
                        with open(variant_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        result.append(BootstrapFile(
                            name="USER",
                            path=variant_path,
                            content=content,
                            missing=False,
                            file_path=variant_filename,
                        ))
                        user_loaded = True
                        continue
                    except (IOError, OSError):
                        pass

            user_bf = self.load_file("USER")
            if not user_bf.missing and user_bf.content:
                result.append(user_bf)
                user_loaded = True

        return result

    def _check_truncation(self, context: BootstrapContext) -> List[str]:
        """Check if bootstrap files exceed token budgets. Returns warning messages."""
        warnings: List[str] = []

        for bf in context.files:
            if not bf.missing and bf.content:
                if len(bf.content) > self.config.bootstrap_max_chars:
                    warnings.append(
                        f"{bf.name}.md exceeds per-file limit: "
                        f"{len(bf.content)} > {self.config.bootstrap_max_chars} chars"
                    )

        if context.total_chars > self.config.bootstrap_total_max_chars:
            warnings.append(
                f"Total bootstrap {context.total_chars} chars exceeds "
                f"limit of {self.config.bootstrap_total_max_chars}"
            )

        return warnings

    def get_truncation_warnings(self, context: BootstrapContext) -> List[str]:
        """Get truncation warnings for the context."""
        return self._check_truncation(context)

    def format_for_prompt(self, context: BootstrapContext) -> str:
        """Format loaded bootstrap files as a prompt string."""
        parts: List[str] = []

        for bf in context.files:
            if bf.missing or not bf.content:
                continue
            content = bf.content

            # Per-file truncation
            if len(content) > self.config.bootstrap_max_chars:
                content = content[: self.config.bootstrap_max_chars]
                logger.warning(
                    f"Truncated {bf.name}.md to {self.config.bootstrap_max_chars} chars"
                )

            parts.append(f"# {bf.name}.md\n\n{content}\n")

        return "\n".join(parts)

    def load_all(
        self,
        max_tokens: Optional[int] = None,
        session_key: Optional[str] = None,
        trigger: str = "cron",
        hooks: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Load bootstrap files for a given session.

        Args:
            max_tokens: Optional character budget. If provided,
                content will be truncated to approximately fit.
            session_key: Session key for per-session variant filtering.
                Files named like USER@agent:main:dm:alice.md are loaded
                only when session_key matches.
            trigger: "message" excludes HEARTBEAT.md from output.
                "cron"/"heartbeat" include it.
            hooks: Optional dict of {filename: callable(entry_dict) -> entry_dict}
                for overriding file content.

        Returns:
            List of dicts with keys: source (filename), content, truncated, etc.
        """
        all_files = self._load_all_candidates()

        filtered, heartbeat_included = self._filter_by_trigger(all_files, trigger)

        filtered = self._filter_by_session(
            filtered, session_key, os.path.join(self.workspace_dir)
        )

        entries: List[Dict[str, Any]] = []
        total_chars = 0
        max_chars = max_tokens if max_tokens else self.config.bootstrap_total_max_chars
        per_file_max = self.config.bootstrap_max_chars

        for bf in filtered:
            if bf.missing:
                continue
            if bf.name == "HEARTBEAT" and not heartbeat_included:
                continue
            content = bf.content or ""
            truncated = False

            if hooks and bf.name + ".md" in hooks:
                content = hooks[bf.name + ".md"](
                    {"source": bf.name + ".md", "content": content}
                ).get("content", content)

            if len(content) > per_file_max:
                content = content[:per_file_max]
                truncated = True

            total_chars += len(content)

            if total_chars > max_chars and len(content) > 0:
                available = max_chars - (total_chars - len(content))
                if available < 0:
                    available = 0
                if len(content) > available:
                    content = content[:available]
                    truncated = True

            if content:
                entries.append({
                    "source": bf.file_path if bf.file_path else bf.name + ".md",
                    "content": content,
                    "truncated": truncated,
                    "_truncated": truncated,
                })

        return entries


# Standalone functions


def get_bootstrap_file_path(
    workspace_dir: str,
    filename: str,
    agent_id: str,
    account_id: Optional[str] = None,
) -> str:
    """Get the resolved path for a bootstrap file."""
    workspace_dir = os.path.expanduser(workspace_dir)

    agent_path = os.path.join(workspace_dir, "agents", agent_id, filename)
    if os.path.exists(agent_path):
        return agent_path

    if account_id and filename == "USER.md":
        account_path = os.path.join(workspace_dir, "accounts", account_id, filename)
        if os.path.exists(account_path):
            return account_path

    return os.path.join(workspace_dir, filename)


def format_bootstrap_warning(
    truncated_files: List[str],
    total_chars: int,
    limit: int,
) -> str:
    """Format a bootstrap truncation warning message."""
    parts = ["⚠️ Bootstrap truncation warning:"]
    if truncated_files:
        parts.append(f"  Truncated files: {', '.join(truncated_files)}")
    parts.append(f"  Total chars: {total_chars} / {limit} limit")
    return "\n".join(parts)
