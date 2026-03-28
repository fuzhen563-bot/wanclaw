"""
Token counting utility using tiktoken.
Falls back to approximate counting if tiktoken unavailable.
"""

import os
from functools import lru_cache
from typing import Optional

_tiktoken_encoder = None

def get_encoder():
    """Lazy-load tiktoken encoder."""
    global _tiktoken_encoder
    if _tiktoken_encoder is None:
        try:
            import tiktoken
            _tiktoken_encoder = tiktoken.get_encoding("cl100k_base")
        except ImportError:
            return None
    return _tiktoken_encoder

def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """
    Count tokens in text.
    Uses tiktoken for accuracy, falls back to len//4.
    """
    encoder = get_encoder()
    if encoder is not None:
        return len(encoder.encode(text))
    # Fallback: ~4 chars per token (rough approximation)
    return max(1, len(text) // 4)

def count_messages_tokens(messages: list, model: str = "gpt-4o") -> int:
    """
    Count tokens for a messages array (OpenAI chat format).
    Accounts for role/header overhead per message.
    """
    total = 0
    encoder = get_encoder()
    overhead = 4  # tokens per message for roles, separators

    if encoder is not None:
        for msg in messages:
            total += overhead
            total += len(encoder.encode(msg.get("content", "")))
            if msg.get("name"):
                total += len(encoder.encode(msg["name"]))
    else:
        for msg in messages:
            total += overhead + max(1, len(msg.get("content", "")) // 4)
    return total
