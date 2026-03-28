"""
ContextAssembly — assembles Bootstrap + Skills + Transcript into final prompt.

Respects max_tokens budget, maxSkillsInPrompt, maxSkillFileBytes,
and produces either a string or a structured message list.
"""
import logging
from typing import List, Dict, Any, Optional, Union

logger = logging.getLogger(__name__)


def _skill_tokens(skill: Dict[str, Any]) -> int:
    return skill.get("tokens", len(skill.get("content", "")) // 4)


class ContextAssembly:
    """
    Assembles bootstrap entries, skills, and transcript into a final context.

    The pipeline:
      1. Bootstrap files (SOUL, IDENTITY, USER, MEMORY, HEARTBEAT)
      2. Selected skills (subject to maxSkillsInPrompt, maxSkillFileBytes)
      3. Transcript entries (subject to remaining token budget)
    """

    def __init__(
        self,
        bootstrap_entries: List[Dict[str, Any]],
        skills: List[Dict[str, Any]],
        transcript_entries: List[Dict[str, Any]],
    ):
        self.bootstrap_entries = bootstrap_entries
        self.skills = skills
        self.transcript_entries = transcript_entries

    def _bootstrap_text(self) -> str:
        parts = []
        for entry in self.bootstrap_entries:
            source = entry.get("source", "")
            content = entry.get("content", "")
            priority = entry.get("priority", 99)
            parts.append((priority, source, content))
        parts.sort(key=lambda x: x[0])
        return "\n\n".join(f"# {src}\n\n{content}" for _, src, content in parts)

    def _skills_text(
        self,
        max_skills: Optional[int] = None,
        max_skill_bytes: Optional[int] = None,
    ) -> str:
        selected = self.skills[:max_skills] if max_skills else self.skills
        parts = []
        for skill in selected:
            content = skill.get("content", "")
            name = skill.get("name", "")
            if max_skill_bytes and len(content) > max_skill_bytes:
                compact = skill.get("compact")
                if compact:
                    content = compact
                else:
                    content = (
                        f"# {name}\n\n"
                        f"{skill.get('description', '')}\n\n"
                        "## Usage\n\n"
                        "[Content truncated — see full skill definition]"
                    )
            parts.append(content)
        return "\n\n".join(parts)

    def _transcript_text(self) -> str:
        parts = []
        for entry in self.transcript_entries:
            role = entry.get("role", "unknown")
            content = entry.get("content", "")
            tool_name = entry.get("tool_name")
            if tool_name:
                parts.append(f"[{role}:{tool_name}] {content}")
            else:
                parts.append(f"[{role}] {content}")
        return "\n".join(parts)

    def assemble(
        self,
        max_tokens: Optional[int] = None,
        reserved_for_user: int = 0,
        maxSkillsInPrompt: Optional[int] = None,
        maxSkillFileBytes: Optional[int] = None,
    ) -> Union[str, Dict[str, Any]]:
        """Assemble all sources into a string prompt."""
        available = (max_tokens - reserved_for_user) if max_tokens else None

        bootstrap = self._bootstrap_text()
        skills = self._skills_text(max_skills=maxSkillsInPrompt, max_skill_bytes=maxSkillFileBytes)
        transcript = self._transcript_text()

        parts = []
        if bootstrap:
            parts.append(bootstrap)
        if skills:
            parts.append(skills)
        if transcript:
            parts.append(transcript)

        assembled = "\n\n".join(parts)

        if available is not None and len(assembled) > available:
            assembled = assembled[:available]
            result: Dict[str, Any] = {
                "content": assembled,
                "_truncated": True,
                "truncated": True,
            }
            return result

        return assembled

    def assemble_messages(self) -> List[Dict[str, str]]:
        """Assemble into a role-structured message list with system first."""
        bootstrap_text = self._bootstrap_text()
        messages: List[Dict[str, str]] = []
        if bootstrap_text:
            messages.append({"role": "system", "content": bootstrap_text})

        for entry in self.transcript_entries:
            role = entry.get("role", "user")
            content = entry.get("content", "")
            msg: Dict[str, str] = {"role": role, "content": content}
            if entry.get("tool_name"):
                msg["name"] = entry["tool_name"]
            messages.append(msg)

        return messages
