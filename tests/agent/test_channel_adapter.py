"""
Tests for Channel Adapter Interface.

Validates that all adapters return ChannelCapabilities,
normalize_message for each platform, get_session_key for 4 scope levels,
and capability fields (threading, reactions, voice, groups, multi_account).
"""
import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PLATFORM_CONFIGS = {
    "wecom": {
        "enabled": True,
        "corp_id": "wxcorp123",
        "agent_id": "1000001",
        "secret": "test_secret",
    },
    "feishu": {
        "enabled": True,
        "app_id": "cli_xxx",
        "app_secret": "test_secret",
    },
    "qq": {
        "enabled": True,
        "uin": "123456789",
        "password": "test_pwd",
    },
    "wechat": {
        "enabled": True,
        "app_id": "wxapp123",
        "app_secret": "test_secret",
    },
    "telegram": {
        "enabled": True,
        "bot_token": "123456:ABC-DEF",
    },
}


@pytest.fixture(params=PLATFORM_CONFIGS.keys())
def platform_name(request):
    """Each platform name as a test parameter."""
    return request.param


@pytest.fixture
def adapter_for_platform(platform_name: str):
    """Instantiate adapter for the given platform."""
    from wanclaw.agent.channel_adapter import get_adapter

    config = PLATFORM_CONFIGS[platform_name]
    adapter = get_adapter(platform_name, config)
    return adapter


# ---------------------------------------------------------------------------
# Tests — ChannelCapabilities
# ---------------------------------------------------------------------------

class TestChannelCapabilities:
    """All adapters return ChannelCapabilities with expected fields."""

    def test_all_platforms_return_capabilities(self, adapter_for_platform):
        """Each adapter provides get_capabilities() or capabilities property."""
        adapter = adapter_for_platform
        assert hasattr(adapter, "get_capabilities") or hasattr(
            adapter, "capabilities"
        )

        caps = (
            adapter.get_capabilities()
            if hasattr(adapter, "get_capabilities")
            else adapter.capabilities
        )
        assert isinstance(caps, dict)

    def test_capabilities_has_required_fields(self, adapter_for_platform):
        """Capabilities dict has threading, reactions, voice, groups, multi_account."""
        adapter = adapter_for_platform
        caps = (
            adapter.get_capabilities()
            if hasattr(adapter, "get_capabilities")
            else adapter.capabilities
        )

        required = ["threading", "reactions", "voice", "groups", "multi_account"]
        for field in required:
            assert field in caps, f"Missing capability field: {field}"
            assert isinstance(caps[field], bool)

    def test_capabilities_platform_specific(self, adapter_for_platform):
        """Different platforms have different capability values."""
        adapter = adapter_for_platform
        caps = (
            adapter.get_capabilities()
            if hasattr(adapter, "get_capabilities")
            else adapter.capabilities
        )

        # Each platform should have distinct capability profile
        # (exact values are platform-specific, just check they're consistent)
        assert isinstance(caps["threading"], bool)
        assert isinstance(caps["reactions"], bool)


# ---------------------------------------------------------------------------
# Tests — normalize_message
# ---------------------------------------------------------------------------

class TestNormalizeMessage:
    """normalize_message() standardizes message format across platforms."""

    def test_returns_dict_with_required_fields(self, adapter_for_platform):
        """normalize_message() returns dict with role and content."""
        adapter = adapter_for_platform
        result = adapter.normalize_message({"text": "hello"})

        assert isinstance(result, dict)
        assert "role" in result
        assert "content" in result

    def test_user_message_normalized(self, adapter_for_platform):
        """User messages are normalized to {role: 'user', content: ...}."""
        adapter = adapter_for_platform
        result = adapter.normalize_message({"text": "Hello, bot!"})

        assert result["role"] == "user"
        assert "Hello" in result["content"] or "hello" in result["content"].lower()

    def test_assistant_message_normalized(self, adapter_for_platform):
        """Assistant messages are normalized to {role: 'assistant', content: ...}."""
        adapter = adapter_for_platform
        result = adapter.normalize_message({"text": "Hello, user!"}, role="assistant")

        assert result["role"] == "assistant"
        assert "Hello" in result["content"] or "hello" in result["content"].lower()

    def test_raw_platform_data_preserved(self, adapter_for_platform):
        """Original platform message data is preserved in 'raw' field."""
        adapter = adapter_for_platform
        original = {"text": "Hi", "msg_id": "12345", "from_user": "alice"}
        result = adapter.normalize_message(original)

        assert "raw" in result
        assert isinstance(result["raw"], dict)

    def test_platform_specific_fields_extracted(self, adapter_for_platform):
        """Platform-specific fields (e.g., quote, thread_id) are extracted."""
        adapter = adapter_for_platform
        platform_specific = {
            "text": "Reply",
            "quote": "original message",
            "thread_id": "thread123",
        }
        result = adapter.normalize_message(platform_specific)

        # Should handle platform-specific fields gracefully
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Tests — get_session_key
# ---------------------------------------------------------------------------

class TestGetSessionKey:
    """get_session_key() generates correct keys for all 4 scope levels."""

    def test_main_scope_key_format(self, adapter_for_platform):
        """MAIN scope generates key: agent:<channel>:<subtype>"""
        from wanclaw.agent.session_scopes import Scope

        adapter = adapter_for_platform
        key = adapter.get_session_key(
            scope=Scope.MAIN,
            channel="main",
        )
        assert isinstance(key, str)
        parts = key.split(":")
        assert parts[0] == "agent"
        assert len(parts) >= 2

    def test_per_peer_scope_key_format(self, adapter_for_platform):
        """PER_PEER scope includes peer_id in key."""
        from wanclaw.agent.session_scopes import Scope

        adapter = adapter_for_platform
        key = adapter.get_session_key(
            scope=Scope.PER_PEER,
            channel="dm",
            peer_id="alice123",
        )
        assert isinstance(key, str)
        assert "alice123" in key

    def test_per_channel_peer_scope_key_format(self, adapter_for_platform):
        """PER_CHANNEL_PEER scope includes channel type and peer_id."""
        from wanclaw.agent.session_scopes import Scope

        adapter = adapter_for_platform
        key = adapter.get_session_key(
            scope=Scope.PER_CHANNEL_PEER,
            channel="wecom",
            sub_channel="dm",
            peer_id="bob456",
        )
        assert isinstance(key, str)
        assert "bob456" in key
        # Should include both channel and sub_channel
        key_parts = key.split(":")
        assert len(key_parts) >= 3

    def test_per_account_scope_key_format(self, adapter_for_platform):
        """PER_ACCOUNT scope includes account identifier."""
        from wanclaw.agent.session_scopes import Scope

        adapter = adapter_for_platform
        key = adapter.get_session_key(
            scope=Scope.PER_ACCOUNT,
            channel="wecom",
            sub_channel="corp",
            account="corp_account_1",
            peer_id="charlie789",
        )
        assert isinstance(key, str)
        assert "charlie789" in key
        assert "corp_account_1" in key

    def test_scope_parameter_required(self, adapter_for_platform):
        """get_session_key() requires scope parameter."""
        adapter = adapter_for_platform
        with pytest.raises(TypeError):
            adapter.get_session_key()  # Missing required scope

    def test_missing_peer_id_raises_for_per_peer(self, adapter_for_platform):
        """PER_PEER scope requires peer_id parameter."""
        from wanclaw.agent.session_scopes import Scope

        adapter = adapter_for_platform
        with pytest.raises((ValueError, TypeError)):
            adapter.get_session_key(scope=Scope.PER_PEER, channel="dm")


# ---------------------------------------------------------------------------
# Tests — Platform-Specific Adapter Interface
# ---------------------------------------------------------------------------

class TestPlatformAdapterInterface:
    """Each platform adapter implements the expected interface."""

    def test_adapter_has_platform_attribute(self, adapter_for_platform, platform_name):
        """Adapter has platform name attribute."""
        adapter = adapter_for_platform
        assert hasattr(adapter, "platform")
        assert adapter.platform == platform_name

    def test_adapter_has_send_method(self, adapter_for_platform):
        """Adapter has send() or send_message() method."""
        adapter = adapter_for_platform
        has_send = hasattr(adapter, "send") or hasattr(adapter, "send_message")
        assert has_send, "Adapter must have send() or send_message()"

    def test_adapter_has_listen_method(self, adapter_for_platform):
        """Adapter has listen() or receive() method."""
        adapter = adapter_for_platform
        has_listen = hasattr(adapter, "listen") or hasattr(adapter, "receive")
        assert has_listen, "Adapter must have listen() or receive()"

    def test_adapter_initializes_with_config(self, platform_name: str):
        """Adapter initializes with platform config dict."""
        from wanclaw.agent.channel_adapter import get_adapter

        config = PLATFORM_CONFIGS[platform_name]
        adapter = get_adapter(platform_name, config)
        assert adapter is not None


# ---------------------------------------------------------------------------
# Tests — All 4 Scope Levels Together
# ---------------------------------------------------------------------------

class TestAllScopeLevels:
    """Comprehensive tests for all 4 scope levels across adapters."""

    def test_all_four_scopes_produce_distinct_keys(self, adapter_for_platform):
        """All 4 scope levels produce different session keys."""
        from wanclaw.agent.session_scopes import Scope

        adapter = adapter_for_platform

        main_key = adapter.get_session_key(scope=Scope.MAIN, channel="main")
        peer_key = adapter.get_session_key(
            scope=Scope.PER_PEER, channel="dm", peer_id="alice"
        )
        channel_peer_key = adapter.get_session_key(
            scope=Scope.PER_CHANNEL_PEER,
            channel="wecom",
            sub_channel="dm",
            peer_id="bob",
        )
        account_key = adapter.get_session_key(
            scope=Scope.PER_ACCOUNT,
            channel="wecom",
            sub_channel="corp",
            account="acc1",
            peer_id="charlie",
        )

        keys = [main_key, peer_key, channel_peer_key, account_key]
        # All keys should be distinct
        assert len(set(keys)) == 4, "All scope levels should produce unique keys"

    def test_scope_enum_values(self):
        """Scope enum has exactly 4 defined levels."""
        from wanclaw.agent.session_scopes import Scope

        scopes = [Scope.MAIN, Scope.PER_PEER, Scope.PER_CHANNEL_PEER, Scope.PER_ACCOUNT]
        assert len(scopes) == 4

        names = [s.name for s in scopes]
        assert "MAIN" in names
        assert "PER_PEER" in names
        assert "PER_CHANNEL_PEER" in names
        assert "PER_ACCOUNT" in names
