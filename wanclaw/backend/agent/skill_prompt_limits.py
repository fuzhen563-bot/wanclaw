"""
Skill Prompt Limits — skill selection, truncation, compact format, and binary search.

Provides functions for selecting skills within token/file-size budgets,
generating compact skill representations, and binary-searching the maximum
number of skills that fit a given budget.
"""
from typing import List, Dict, Any, Optional


def _skill_tokens(skill: Dict[str, Any]) -> int:
    return skill.get("tokens", max(len(skill.get("content", "")) // 4, 10))


def _skill_bytes(skill: Dict[str, Any]) -> int:
    return len(skill.get("content", "") or skill.get("body", ""))


def compact_format(skill: Dict[str, Any]) -> str:
    """Return compact skill format: name + description + ## Usage."""
    name = skill.get("name", "")
    description = skill.get("description", "")
    usage = skill.get("usage", "")
    return (
        f"# {name}\n\n"
        f"{description}\n\n"
        f"## Usage\n\n"
        f"{usage or '[See full skill definition]'}"
    )


def select_skills(
    skills: List[Dict[str, Any]],
    max_skills: int,
    user_input: str = "",
    max_tokens: int = 100000,
    max_skill_file_bytes: Optional[int] = None,
    compact: bool = False,
) -> List[Dict[str, Any]]:
    """Select up to max_skills based on relevance and budget."""
    user_lower = user_input.lower()

    def relevance_score(skill: Dict[str, Any]) -> int:
        score = 0
        keywords = skill.get("keywords", [])
        desc_lower = skill.get("description", "").lower()
        for kw in keywords:
            if kw.lower() in user_lower:
                score += 2
        for kw in keywords:
            if kw.lower() in desc_lower:
                score += 1
        return score

    scored = [(relevance_score(s), _skill_tokens(s), s) for s in skills]
    scored.sort(key=lambda x: (-x[0], x[1]))

    selected: List[Dict[str, Any]] = []
    used_tokens = 0

    for _, tok, skill in scored:
        if len(selected) >= max_skills:
            break
        if used_tokens + tok > max_tokens and selected:
            break

        result = dict(skill)
        content_key = "content" if "content" in result else "body"
        content = result.get(content_key, "")

        if compact:
            result[content_key] = compact_format(skill)
        elif max_skill_file_bytes and len(content) > max_skill_file_bytes:
            result[content_key] = content[:max_skill_file_bytes]

        selected.append(result)
        used_tokens += tok

    return selected


def find_max_skills(
    skills: List[Dict[str, Any]],
    max_tokens: int,
    max_skills: int = 999,
) -> int:
    """Binary search for the maximum number of skills that fit within max_tokens."""
    if max_tokens <= 0 or not skills:
        return 0

    lo, hi = 0, min(max_skills, len(skills))

    def fits(n: int) -> bool:
        total = sum(_skill_tokens(s) for s in skills[:n])
        return total <= max_tokens

    while lo < hi:
        mid = (lo + hi + 1) // 2
        if fits(mid):
            lo = mid
        else:
            hi = mid - 1

    return lo
