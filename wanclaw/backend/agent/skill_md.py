"""WanClaw SKILL.md Parser."""

import re
import yaml
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


FRONTMATTER_PATTERN = re.compile(r'^---\n(.*?)\n---', re.DOTALL)
BREW_FORMULA_PATTERN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9@+._/-]*$')


@dataclass
class SkillRequires:
    bins: List[str] = field(default_factory=list)
    any_bins: List[str] = field(default_factory=list)
    env: List[str] = field(default_factory=list)
    config: List[str] = field(default_factory=list)


@dataclass
class SkillInstallSpec:
    kind: str
    package: Optional[str] = None
    formula: Optional[str] = None
    module: Optional[str] = None
    url: Optional[str] = None
    bins: List[str] = field(default_factory=list)
    os: List[str] = field(default_factory=list)
    label: Optional[str] = None


@dataclass
class SkillMetadata:
    requires: Optional[SkillRequires] = None
    install: List[SkillInstallSpec] = field(default_factory=list)
    primary_env: Optional[str] = None
    always: bool = False
    os: List[str] = field(default_factory=list)
    skill_key: Optional[str] = None
    emoji: Optional[str] = None
    homepage: Optional[str] = None
    permissions: List[str] = field(default_factory=list)
    compatible_version: Optional[str] = None


@dataclass
class SkillDefinition:
    name: str
    description: str
    body: str
    metadata: Optional[SkillMetadata] = None
    user_invocable: bool = True
    disable_model_invocation: bool = False
    file_path: Optional[str] = None
    requires_tools: List[str] = field(default_factory=list)


class SkillMarkdownParser:

    @classmethod
    def parse(cls, content: str, file_path: Optional[str] = None) -> Dict[str, Any]:
        frontmatter = cls.parse_frontmatter(content)

        match = FRONTMATTER_PATTERN.match(content)
        body = content[match.end():].lstrip('\n') if match else content

        name = frontmatter.get('name', 'unnamed-skill')
        description = frontmatter.get('description', '')
        user_invocable = frontmatter.get('user-invocable', True)
        disable_model_invocation = frontmatter.get('disable-model-invocation', False)

        requires = cls._extract_requires(frontmatter)
        primary_env = frontmatter.get('primaryEnv')
        always = frontmatter.get('always', False)
        os_list = frontmatter.get('os', [])

        install = cls._extract_install(frontmatter)
        wanclaw = cls._extract_wanclaw(frontmatter)

        return {
            'name': name,
            'description': description,
            'body': body,
            'requires': requires,
            'primaryEnv': primary_env,
            'always': always,
            'os': os_list,
            'user-invocable': user_invocable,
            'disable-model-invocation': disable_model_invocation,
            'install': install,
            'wanclaw': wanclaw,
        }

    @classmethod
    def parse_frontmatter(cls, content: str) -> Dict[str, Any]:
        match = FRONTMATTER_PATTERN.match(content)
        if not match:
            if content.lstrip().startswith('---'):
                raise ValueError("Missing frontmatter closing delimiter")
            return {}
        yaml_content = match.group(1)
        try:
            return yaml.safe_load(yaml_content) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Malformed YAML: {e}")

    @classmethod
    def _extract_requires(cls, frontmatter: Dict[str, Any]) -> Dict[str, List[str]]:
        openclaw = frontmatter.get('metadata', {}).get('openclaw', {})
        requires_raw = openclaw.get('requires') or frontmatter.get('requires') or {}
        return {
            'env': requires_raw.get('env', []),
            'bins': requires_raw.get('bins', []),
            'config': requires_raw.get('config', []),
            'any_bins': requires_raw.get('any_bins', []),
        }

    @classmethod
    def _extract_install(cls, frontmatter: Dict[str, Any]) -> Dict[str, Any]:
        openclaw = frontmatter.get('metadata', {}).get('openclaw', {})
        install_raw = openclaw.get('install') or frontmatter.get('install') or {}
        install: Dict[str, Any] = {}
        for kind in ['brew', 'node', 'uv', 'download']:
            items = install_raw.get(kind, [])
            if items:
                install[kind] = items
        return install

    @classmethod
    def _extract_wanclaw(cls, frontmatter: Dict[str, Any]) -> Dict[str, Any]:
        openclaw = frontmatter.get('metadata', {}).get('openclaw', {})
        wanclaw_raw = openclaw.get('wanclaw') or frontmatter.get('wanclaw') or {}
        return {
            'tools': wanclaw_raw.get('tools', []),
            'sandbox': {
                'allowed': wanclaw_raw.get('sandbox', {}).get('allowed', []),
                'denied': wanclaw_raw.get('sandbox', {}).get('denied', []),
            },
            'maxTokens': wanclaw_raw.get('maxTokens'),
            'maxSkillsInPrompt': wanclaw_raw.get('maxSkillsInPrompt'),
            'maxSkillFileBytes': wanclaw_raw.get('maxSkillFileBytes'),
            'compactFormat': wanclaw_raw.get('compactFormat'),
        }


def parse_skill_md(content: str, file_path: Optional[str] = None) -> Dict[str, Any]:
    return SkillMarkdownParser.parse(content, file_path)


def is_valid_install_kind(kind: str) -> bool:
    return kind in {"brew", "node", "go", "uv", "download"}
