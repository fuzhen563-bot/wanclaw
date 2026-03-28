"""
Shared fixtures for agent tests.
"""
import json
import os
import tempfile
from pathlib import Path
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_llm_client() -> AsyncMock:
    """AsyncMock LLM client that returns predictable responses."""
    client = AsyncMock()
    client.chat = AsyncMock(
        return_value={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Mock LLM response",
                    }
                }
            ]
        }
    )
    client.chat_completions = AsyncMock(
        return_value=MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(content="Mock LLM response", role="assistant")
                )
            ]
        )
    )
    return client


@pytest.fixture
def mock_redis() -> MagicMock:
    """Redis mock that mimics aioredis behavior."""
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.setex = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    redis.exists = AsyncMock(return_value=0)
    redis.incr = AsyncMock(return_value=1)
    redis.decr = AsyncMock(return_value=0)
    redis.close = AsyncMock()
    redis.smembers = AsyncMock(return_value=set())
    redis.sadd = AsyncMock(return_value=1)
    redis.srem = AsyncMock(return_value=1)
    redis.lrange = AsyncMock(return_value=[])
    redis.lpush = AsyncMock(return_value=1)
    redis.rpush = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    redis.ttl = AsyncMock(return_value=-1)
    return redis


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """
    Temporary directory with standard bootstrap files:
    SOUL.md, IDENTITY.md, USER.md, MEMORY.md, HEARTBEAT.md
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    (workspace / "SOUL.md").write_text(
        "You are a helpful AI assistant powered by OpenClaw architecture."
    )
    (workspace / "IDENTITY.md").write_text(
        "Name: TestAgent\nVersion: 1.0.0"
    )
    (workspace / "USER.md").write_text(
        "User Preferences:\n- Language: English"
    )
    (workspace / "MEMORY.md").write_text(
        "# Memory Log\n\n## 2024-01-01\n- Remembered that user prefers verbose output"
    )
    (workspace / "HEARTBEAT.md").write_text(
        "cron: */5 * * * *\nmessage: System heartbeat OK"
    )

    return workspace


@pytest.fixture
def sample_skill_md() -> str:
    """A sample SKILL.md content for testing."""
    return """---
name: test_skill
description: A test skill for unit testing
version: 1.0.0
author: test
mode: agent

requires:
  env:
    - OPENAI_API_KEY
  bins:
    - python3
  config:
    - api_endpoint

primaryEnv: python3
always: false

os: [linux, darwin]

user-invocable: true
disable-model-invocation: false

install:
  brew:
    - coreutils
  node:
    - typescript
  uv:
    - requests

wanclaw:
  tools: [bash, write, read]
  sandbox:
    allowed: [bash, read]
    denied: [delete]
  maxTokens: 8000
  maxSkillsInPrompt: 5
  maxSkillFileBytes: 15000
  compactFormat: true
---

# Test Skill

## Usage

```bash
python3 test.py
```

## Description

This is a test skill used for unit testing the SKILL.md parser.
"""


@pytest.fixture
def sample_bootstrap_files() -> dict[str, str]:
    """Dict of bootstrap file contents keyed by filename."""
    return {
        "SOUL.md": "You are a helpful AI assistant.",
        "IDENTITY.md": "Name: TestAgent\nVersion: 1.0.0",
        "USER.md": "User Preferences:\n- Language: English",
        "MEMORY.md": "# Memory Log\n\n## 2024-01-01\n- Remembered something",
        "HEARTBEAT.md": "cron: */5 * * * *\nmessage: System heartbeat OK",
    }


@pytest.fixture
def mock_channel_adapter() -> MagicMock:
    """Mock channel adapter with standard interface."""
    adapter = MagicMock()
    adapter.platform = "test"
    adapter.get_session_key = MagicMock(return_value="agent:main:test")
    adapter.normalize_message = MagicMock(
        return_value={"role": "user", "content": "test message", "raw": {}}
    )
    adapter.get_capabilities = MagicMock(
        return_value={
            "threading": False,
            "reactions": False,
            "voice": False,
            "groups": False,
            "multi_account": False,
        }
    )
    return adapter


@pytest.fixture
def sample_transcript_entries() -> list[dict[str, Any]]:
    """Sample transcript entries for testing."""
    return [
        {
            "role": "user",
            "content": "Hello, how are you?",
            "timestamp": "2024-01-01T10:00:00Z",
            "session": "agent:main:test",
        },
        {
            "role": "assistant",
            "content": "I'm doing well, thank you!",
            "timestamp": "2024-01-01T10:00:01Z",
            "session": "agent:main:test",
        },
        {
            "role": "tool",
            "content": "Tool result",
            "tool_name": "bash",
            "timestamp": "2024-01-01T10:00:02Z",
            "session": "agent:main:test",
        },
    ]
