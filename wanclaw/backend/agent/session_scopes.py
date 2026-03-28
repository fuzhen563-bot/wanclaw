"""
Session Scope Generator — 4-level session key generation.

Scope levels:
  MAIN              → agent:<channel>:<subtype>
  PER_PEER          → agent:<channel>:<subtype>:<peer_id>
  PER_CHANNEL_PEER  → agent:<channel>:<sub_channel>:<sub_sub_channel>:<peer_id>
  PER_ACCOUNT       → agent:<channel>:<sub_channel>:<sub_sub_channel>:<sub_sub_sub_channel>:<peer_id>

Each scope level adds granularity for session isolation.
"""
import re
from enum import Enum
from typing import Dict, List, Optional


class Scope(Enum):
    MAIN = "main"
    PER_PEER = "per_peer"
    PER_CHANNEL_PEER = "per_channel_peer"
    PER_ACCOUNT = "per_account"


def _sanitize_peer_id(peer_id: str) -> str:
    """Remove or replace special characters from peer IDs."""
    peer_id = re.sub(r"[@/\\:]", "_", peer_id)
    return peer_id


class SessionScopeGenerator:
    """
    Generates session keys at 4 scope levels.

    Deterministic: same inputs always produce same key.
    Peer IDs are sanitized to produce safe session identifiers.
    """

    def generate_key(
        self,
        scope: Scope,
        channel: str = "main",
        sub_channel: Optional[str] = None,
        sub_sub_channel: Optional[str] = None,
        sub_sub_sub_channel: Optional[str] = None,
        peer_id: Optional[str] = None,
        account: Optional[str] = None,
        **extra: str,
    ) -> str:
        """Generate session key for the given scope and parameters."""
        if scope == Scope.MAIN:
            subtype = sub_channel or "main"
            return f"agent:{channel}:{subtype}"

        if scope == Scope.PER_PEER:
            if peer_id is None:
                raise TypeError("peer_id is required for PER_PEER scope")
            subtype = sub_channel or "dm"
            return f"agent:{channel}:{subtype}:{_sanitize_peer_id(peer_id)}"

        if scope == Scope.PER_CHANNEL_PEER:
            if peer_id is None:
                raise TypeError("peer_id is required for PER_CHANNEL_PEER scope")
            return (
                f"agent:{channel}:{sub_channel}:{sub_sub_channel}:"
                f"{_sanitize_peer_id(peer_id)}"
            )

        if scope == Scope.PER_ACCOUNT:
            if peer_id is None:
                raise TypeError("peer_id is required for PER_ACCOUNT scope")
            if account is not None:
                return (
                    f"agent:{channel}:{sub_channel}:{sub_sub_channel}:"
                    f"{sub_sub_sub_channel}:{account}:{_sanitize_peer_id(peer_id)}"
                )
            elif sub_sub_sub_channel is not None:
                return (
                    f"agent:{channel}:{sub_channel}:{sub_sub_channel}:"
                    f"{sub_sub_sub_channel}:{_sanitize_peer_id(peer_id)}"
                )
            else:
                return (
                    f"agent:{channel}:{sub_channel}:{sub_sub_channel}:"
                    f"{_sanitize_peer_id(peer_id)}"
                )

        raise ValueError(f"Unknown scope: {scope}")

    def resolve_identity(
        self,
        person_id: str,
        sessions: List[str],
    ) -> List[str]:
        """Return all sessions associated with a person ID."""
        return [s for s in sessions if person_id in s]
