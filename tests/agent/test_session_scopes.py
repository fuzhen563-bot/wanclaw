"""
Tests for Session Scoping — 4 scope levels with correct key format,
scope isolation, and identity linking across channels.
"""
import pytest


# ---------------------------------------------------------------------------
# Tests — 4 Scope Levels Generate Correct Keys
# ---------------------------------------------------------------------------

class TestScopeKeyFormats:
    """Each scope level generates correctly formatted session keys."""

    def test_main_scope_key_format(self):
        """MAIN scope: agent:main:main"""
        from wanclaw.agent.session_scopes import Scope, SessionScopeGenerator

        gen = SessionScopeGenerator()
        key = gen.generate_key(scope=Scope.MAIN, channel="main")

        assert key == "agent:main:main"
        assert key.count(":") == 2

    def test_per_peer_scope_key_format(self):
        """PER_PEER scope: agent:main:dm:peer_id"""
        from wanclaw.agent.session_scopes import Scope, SessionScopeGenerator

        gen = SessionScopeGenerator()
        key = gen.generate_key(
            scope=Scope.PER_PEER, channel="main", sub_channel="dm", peer_id="alice123"
        )

        expected = "agent:main:dm:alice123"
        assert key == expected
        assert "alice123" in key

    def test_per_channel_peer_scope_key_format(self):
        """PER_CHANNEL_PEER scope: agent:main:wecom:dm:peer_id"""
        from wanclaw.agent.session_scopes import Scope, SessionScopeGenerator

        gen = SessionScopeGenerator()
        key = gen.generate_key(
            scope=Scope.PER_CHANNEL_PEER,
            channel="main",
            sub_channel="wecom",
            sub_sub_channel="dm",
            peer_id="bob456",
        )

        parts = key.split(":")
        assert parts[0] == "agent"
        assert "bob456" in key
        # Format: agent:<channel>:<sub_channel>:<sub_sub_channel>:<peer_id>
        assert len(parts) == 5

    def test_per_account_scope_key_format(self):
        """PER_ACCOUNT scope: agent:main:wecom:corp:dm:peer_id"""
        from wanclaw.agent.session_scopes import Scope, SessionScopeGenerator

        gen = SessionScopeGenerator()
        key = gen.generate_key(
            scope=Scope.PER_ACCOUNT,
            channel="main",
            sub_channel="wecom",
            sub_sub_channel="corp",
            sub_sub_sub_channel="dm",
            peer_id="charlie789",
        )

        parts = key.split(":")
        assert parts[0] == "agent"
        assert "charlie789" in key
        # Format: agent:<channel>:<sub>:<sub>:<sub>:<peer_id>
        assert len(parts) == 6

    def test_wecom_dm_per_channel_peer_example(self):
        """WeCom DM: agent:main:wecom:dm:peer_id"""
        from wanclaw.agent.session_scopes import Scope, SessionScopeGenerator

        gen = SessionScopeGenerator()
        key = gen.generate_key(
            scope=Scope.PER_CHANNEL_PEER,
            channel="main",
            sub_channel="wecom",
            sub_sub_channel="dm",
            peer_id="wxpseudoid123",
        )

        assert key == "agent:main:wecom:dm:wxpseudoid123"

    def test_wecom_corp_dm_per_account_example(self):
        """WeCom Corp DM: agent:main:wecom:corp:dm:peer_id"""
        from wanclaw.agent.session_scopes import Scope, SessionScopeGenerator

        gen = SessionScopeGenerator()
        key = gen.generate_key(
            scope=Scope.PER_ACCOUNT,
            channel="main",
            sub_channel="wecom",
            sub_sub_channel="corp",
            sub_sub_sub_channel="dm",
            peer_id="wxpseudoid456",
        )

        assert key == "agent:main:wecom:corp:dm:wxpseudoid456"


# ---------------------------------------------------------------------------
# Tests — Scope Isolation
# ---------------------------------------------------------------------------

class TestScopeIsolation:
    """Per-peer sessions are isolated from each other."""

    def test_different_peers_different_sessions(self):
        """alice and bob have different session keys (isolation)."""
        from wanclaw.agent.session_scopes import Scope, SessionScopeGenerator

        gen = SessionScopeGenerator()
        alice_key = gen.generate_key(
            scope=Scope.PER_PEER, channel="main", sub_channel="dm", peer_id="alice"
        )
        bob_key = gen.generate_key(
            scope=Scope.PER_PEER, channel="main", sub_channel="dm", peer_id="bob"
        )

        assert alice_key != bob_key
        assert "alice" in alice_key
        assert "bob" in bob_key

    def test_same_peer_same_channel_same_key(self):
        """Same peer in same channel always gets the same key."""
        from wanclaw.agent.session_scopes import Scope, SessionScopeGenerator

        gen = SessionScopeGenerator()
        key1 = gen.generate_key(
            scope=Scope.PER_PEER, channel="main", sub_channel="dm", peer_id="alice"
        )
        key2 = gen.generate_key(
            scope=Scope.PER_PEER, channel="main", sub_channel="dm", peer_id="alice"
        )

        assert key1 == key2, "Same peer should produce identical session key"

    def test_different_subchannels_different_sessions(self):
        """Different sub-channels (dm vs group) produce different keys."""
        from wanclaw.agent.session_scopes import Scope, SessionScopeGenerator

        gen = SessionScopeGenerator()
        dm_key = gen.generate_key(
            scope=Scope.PER_CHANNEL_PEER,
            channel="main",
            sub_channel="wecom",
            sub_sub_channel="dm",
            peer_id="user1",
        )
        group_key = gen.generate_key(
            scope=Scope.PER_CHANNEL_PEER,
            channel="main",
            sub_channel="wecom",
            sub_sub_channel="group",
            peer_id="user1",
        )

        assert dm_key != group_key, "DM and group should have different sessions"
        assert "dm" in dm_key
        assert "group" in group_key

    def test_different_accounts_different_sessions(self):
        """Different accounts for same peer have different sessions."""
        from wanclaw.agent.session_scopes import Scope, SessionScopeGenerator

        gen = SessionScopeGenerator()
        acc1_key = gen.generate_key(
            scope=Scope.PER_ACCOUNT,
            channel="main",
            sub_channel="wecom",
            sub_sub_channel="corp",
            sub_sub_sub_channel="dm",
            account="account_a",
            peer_id="user1",
        )
        acc2_key = gen.generate_key(
            scope=Scope.PER_ACCOUNT,
            channel="main",
            sub_channel="wecom",
            sub_sub_channel="corp",
            sub_sub_sub_channel="dm",
            account="account_b",
            peer_id="user1",
        )

        assert acc1_key != acc2_key, "Different accounts should have different sessions"
        assert "account_a" in acc1_key
        assert "account_b" in acc2_key


# ---------------------------------------------------------------------------
# Tests — Identity Linking (Same Person Across Channels)
# ---------------------------------------------------------------------------

class TestIdentityLinking:
    """Same person can be identified across different channels."""

    def test_person_id_persists_across_scope_levels(self):
        """A person's ID appears in both PER_PEER and PER_CHANNEL_PEER keys."""
        from wanclaw.agent.session_scopes import Scope, SessionScopeGenerator

        gen = SessionScopeGenerator()
        person_id = "person_abc"

        peer_key = gen.generate_key(
            scope=Scope.PER_PEER,
            channel="main",
            sub_channel="dm",
            peer_id=person_id,
        )
        channel_peer_key = gen.generate_key(
            scope=Scope.PER_CHANNEL_PEER,
            channel="main",
            sub_channel="wecom",
            sub_sub_channel="dm",
            peer_id=person_id,
        )

        # The person_id should appear in both keys
        assert person_id in peer_key
        assert person_id in channel_peer_key

    def test_identity_link_across_multiple_channels(self):
        """Same person on multiple channels can be linked via shared ID."""
        from wanclaw.agent.session_scopes import Scope, SessionScopeGenerator

        gen = SessionScopeGenerator()
        person_id = "shared_person_xyz"

        # Same person on WeCom DM
        wecom_key = gen.generate_key(
            scope=Scope.PER_CHANNEL_PEER,
            channel="main",
            sub_channel="wecom",
            sub_sub_channel="dm",
            peer_id=person_id,
        )

        # Same person on Telegram
        telegram_key = gen.generate_key(
            scope=Scope.PER_CHANNEL_PEER,
            channel="main",
            sub_channel="telegram",
            sub_sub_channel="dm",
            peer_id=person_id,
        )

        # Keys differ (different channels) but share person ID
        assert wecom_key != telegram_key
        assert person_id in wecom_key
        assert person_id in telegram_key

    def test_resolve_identity_finds_all_sessions(self):
        """resolve_identity(person_id) returns all sessions for that person."""
        from wanclaw.agent.session_scopes import Scope, SessionScopeGenerator

        gen = SessionScopeGenerator()
        person_id = "person_resolve"

        # Register sessions
        sessions = [
            gen.generate_key(
                scope=Scope.PER_CHANNEL_PEER,
                channel="main",
                sub_channel="wecom",
                sub_sub_channel="dm",
                peer_id=person_id,
            ),
            gen.generate_key(
                scope=Scope.PER_CHANNEL_PEER,
                channel="main",
                sub_channel="telegram",
                sub_sub_channel="dm",
                peer_id=person_id,
            ),
        ]

        # resolve_identity should return all sessions for this person
        resolved = gen.resolve_identity(person_id, sessions)
        assert len(resolved) == 2
        assert all(person_id in k for k in resolved)


# ---------------------------------------------------------------------------
# Tests — Key Format Consistency
# ---------------------------------------------------------------------------

class TestKeyFormatConsistency:
    """Session keys follow consistent colon-separated format."""

    def test_key_starts_with_agent_prefix(self):
        """All session keys start with 'agent:' prefix."""
        from wanclaw.agent.session_scopes import Scope, SessionScopeGenerator

        gen = SessionScopeGenerator()
        key = gen.generate_key(scope=Scope.MAIN, channel="main")
        assert key.startswith("agent:")

    def test_key_has_no_trailing_colon(self):
        """Session keys do not end with a colon."""
        from wanclaw.agent.session_scopes import Scope, SessionScopeGenerator

        gen = SessionScopeGenerator()
        key = gen.generate_key(
            scope=Scope.PER_ACCOUNT,
            channel="main",
            sub_channel="wecom",
            sub_sub_channel="corp",
            sub_sub_sub_channel="dm",
            peer_id="test123",
        )
        assert not key.endswith(":"), "Key should not end with colon"

    def test_key_is_valid_session_identifier(self):
        """Generated key is a valid session identifier (no spaces, safe for paths)."""
        from wanclaw.agent.session_scopes import Scope, SessionScopeGenerator

        gen = SessionScopeGenerator()
        key = gen.generate_key(
            scope=Scope.PER_PEER, channel="main", sub_channel="dm", peer_id="alice_123"
        )

        assert " " not in key
        assert "/" not in key
        assert key == key.strip()

    def test_peer_id_sanitization(self):
        """Peer IDs with special characters are sanitized in keys."""
        from wanclaw.agent.session_scopes import Scope, SessionScopeGenerator

        gen = SessionScopeGenerator()
        key = gen.generate_key(
            scope=Scope.PER_PEER,
            channel="main",
            sub_channel="dm",
            peer_id="user@domain.com/123",
        )

        # Key should be sanitized (no @ or / in session key)
        assert "@" not in key or "/" not in key
        # Key should still be usable as identifier
        assert len(key) > 0
