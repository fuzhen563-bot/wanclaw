"""
WanClaw Skill MD Loader

Loads skills from SKILL.md files (OpenClaw compatible format).
Skills are YAML frontmatter + markdown instructions that the agent can execute.
"""

import os
import re
import yaml
import logging
import hashlib
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class SkillMD:
    def __init__(self, path: str, metadata: Dict, content: str):
        self.path = path
        self.name = metadata.get("name", Path(path).parent.name)
        self.version = metadata.get("version", "1.0.0")
        self.description = metadata.get("description", "")
        self.author = metadata.get("author", "community")
        self.category = metadata.get("category", "custom")
        self.tags = metadata.get("tags", [])
        self.permissions = metadata.get("permissions", [])
        self.tools = metadata.get("tools", [])
        self.entry = metadata.get("entry", "main.py")
        self.content = content
        self.sha256 = hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "category": self.category,
            "tags": self.tags,
            "permissions": self.permissions,
            "tools": self.tools,
            "sha256": self.sha256,
            "path": self.path,
        }


def parse_skill_md(file_path: str) -> Optional[SkillMD]:
    try:
        with open(file_path) as f:
            raw = f.read()
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', raw, re.DOTALL)
        if match:
            metadata = yaml.safe_load(match.group(1)) or {}
            content = match.group(2).strip()
        else:
            metadata = {"name": Path(file_path).stem}
            content = raw
        return SkillMD(file_path, metadata, content)
    except Exception as e:
        logger.warning(f"Failed to parse {file_path}: {e}")
        return None


class SkillMDLoader:
    def __init__(self, skills_dir: str = None):
        self.skills_dir = Path(skills_dir or os.path.expanduser("~/.wanclaw/skills"))
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.skills: Dict[str, SkillMD] = {}

    def load_all(self):
        self.skills.clear()
        for md_file in self.skills_dir.rglob("SKILL.md"):
            skill = parse_skill_md(str(md_file))
            if skill:
                self.skills[skill.name] = skill
                logger.info(f"Loaded skill: {skill.name} v{skill.version}")
        logger.info(f"Loaded {len(self.skills)} skills from {self.skills_dir}")

    def get_skill(self, name: str) -> Optional[SkillMD]:
        return self.skills.get(name)

    def list_skills(self, category: str = None) -> List[Dict]:
        results = []
        for skill in self.skills.values():
            if category and skill.category != category:
                continue
            results.append(skill.to_dict())
        return results

    def search(self, query: str) -> List[Dict]:
        query_lower = query.lower()
        results = []
        for skill in self.skills.values():
            if (query_lower in skill.name.lower() or
                query_lower in skill.description.lower() or
                any(query_lower in tag.lower() for tag in skill.tags)):
                results.append(skill.to_dict())
        return results

    def get_stats(self) -> Dict:
        categories = {}
        for skill in self.skills.values():
            categories[skill.category] = categories.get(skill.category, 0) + 1
        return {"total": len(self.skills), "categories": categories}


def create_example_skill_md(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    content = """---
name: hello-world
version: 1.0.0
description: A simple example skill that greets the user
author: wanclaw
category: custom
tags: [example, greeting]
permissions: []
tools: []
---

# Hello World Skill

This skill demonstrates the SKILL.md format.

## Usage

When the user says "hello", respond with a friendly greeting.

## Implementation

```python
async def run(params):
    name = params.get("name", "friend")
    return f"Hello, {name}! I'm WanClaw, your AI assistant."
```
"""
    with open(path, "w") as f:
        f.write(content)
    logger.info(f"Example skill created at {path}")


_loader: Optional[SkillMDLoader] = None


def get_skill_md_loader(**kwargs) -> SkillMDLoader:
    global _loader
    if _loader is None:
        _loader = SkillMDLoader(**kwargs)
        _loader.load_all()
    return _loader
