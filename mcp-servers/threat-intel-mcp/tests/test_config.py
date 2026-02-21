"""
Tests for threat_intel_mcp.config module.
"""

import pytest
from threat_intel_mcp.config import (
    validate_ip,
    validate_hash,
    validate_domain,
    validate_ioc_type,
    ThreatCache,
    FeedType,
    Severity,
    IOCType,
    THREAT_FEEDS,
    get_feed,
    get_enabled_feeds,
    get_ip_feeds,
    get_timestamp,
    calculate_severity,
)


class TestValidateIP:
    """Tests for IP validation."""

    def test_valid_ipv4(self):
        is_valid, error = validate_ip("198.51.100.1")
        assert is_valid is True
        assert error is None

    def test_valid_ipv4_edge_cases(self):
        assert validate_ip("0.0.0.0")[0] is True
        assert validate_ip("255.255.255.255")[0] is True
        assert validate_ip("8.8.8.8")[0] is True

    def test_invalid_ip_format(self):
        is_valid, error = validate_ip("not-an-ip")
        assert is_valid is False
        assert "Invalid IP address" in error

    def test_invalid_ip_out_of_range(self):
        is_valid, error = validate_ip("256.1.1.1")
        assert is_valid is False

    def test_invalid_ip_empty(self):
        is_valid, error = validate_ip("")
        assert is_valid is False

    def test_valid_ipv6(self):
        is_valid, error = validate_ip("::1")
        assert is_valid is True

    def test_valid_ipv6_full(self):
        is_valid, error = validate_ip("2001:0db8:85a3:0000:0000:8a2e:0370:7334")
        assert is_valid is True


class TestValidateHash:
    """Tests for hash validation."""

    def test_valid_md5(self):
        is_valid, hash_type, error = validate_hash("d41d8cd98f00b204e9800998ecf8427e")
        assert is_valid is True
        assert hash_type == "md5"
        assert error is None

    def test_valid_sha1(self):
        is_valid, hash_type, error = validate_hash("da39a3ee5e6b4b0d3255bfef95601890afd80709")
        assert is_valid is True
        assert hash_type == "sha1"

    def test_valid_sha256(self):
        is_valid, hash_type, error = validate_hash("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
        assert is_valid is True
        assert hash_type == "sha256"

    def test_invalid_hash_length(self):
        is_valid, hash_type, error = validate_hash("abc123")
        assert is_valid is False
        assert hash_type is None
        assert "Invalid hash format" in error

    def test_invalid_hash_chars(self):
        is_valid, hash_type, error = validate_hash("zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz")  # 32 z's
        assert is_valid is False

    def test_hash_case_insensitive(self):
        is_valid, hash_type, error = validate_hash("D41D8CD98F00B204E9800998ECF8427E")
        assert is_valid is True
        assert hash_type == "md5"


class TestValidateDomain:
    """Tests for domain validation."""

    def test_valid_domain(self):
        is_valid, error = validate_domain("example.com")
        assert is_valid is True

    def test_valid_subdomain(self):
        is_valid, error = validate_domain("www.example.com")
        assert is_valid is True

    def test_valid_multi_subdomain(self):
        is_valid, error = validate_domain("sub.domain.example.co.uk")
        assert is_valid is True

    def test_invalid_domain_no_tld(self):
        is_valid, error = validate_domain("localhost")
        assert is_valid is False

    def test_invalid_domain_ip(self):
        is_valid, error = validate_domain("198.51.100.1")
        assert is_valid is False


class TestValidateIOCType:
    """Tests for IOC type validation."""

    def test_valid_ip_type(self):
        is_valid, error = validate_ioc_type("ip")
        assert is_valid is True

    def test_valid_ip_port_type(self):
        is_valid, error = validate_ioc_type("ip:port")
        assert is_valid is True

    def test_valid_domain_type(self):
        is_valid, error = validate_ioc_type("domain")
        assert is_valid is True

    def test_invalid_type(self):
        is_valid, error = validate_ioc_type("invalid")
        assert is_valid is False
        assert "Invalid IOC type" in error


class TestThreatCache:
    """Tests for thread-safe cache."""

    def test_set_and_get(self):
        cache = ThreatCache(max_size=10)
        cache.set("test_key", {"data": "value"})
        result = cache.get("test_key")
        assert result == {"data": "value"}

    def test_get_nonexistent(self):
        cache = ThreatCache()
        result = cache.get("nonexistent")
        assert result is None

    def test_cache_expiry(self):
        cache = ThreatCache(default_ttl=0)  # Immediate expiry
        cache.set("test_key", "value")
        # Should be expired immediately
        import time
        time.sleep(0.01)
        result = cache.get("test_key")
        assert result is None

    def test_cache_size_limit(self):
        cache = ThreatCache(max_size=2)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")  # Should evict key1

        stats = cache.stats()
        assert stats["size"] <= 2

    def test_delete(self):
        cache = ThreatCache()
        cache.set("test_key", "value")
        assert cache.delete("test_key") is True
        assert cache.get("test_key") is None

    def test_delete_nonexistent(self):
        cache = ThreatCache()
        assert cache.delete("nonexistent") is False

    def test_clear(self):
        cache = ThreatCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.stats()["size"] == 0

    def test_stats(self):
        cache = ThreatCache(max_size=10)
        cache.set("key1", "value1")
        stats = cache.stats()
        assert stats["size"] == 1
        assert stats["max_size"] == 10
        assert "key1" in stats["keys"]


class TestThreatFeeds:
    """Tests for threat feed configuration."""

    def test_feeds_defined(self):
        assert len(THREAT_FEEDS) > 0

    def test_required_feeds_exist(self):
        required = ["feodo_tracker", "urlhaus_recent", "cisa_kev", "tor_exit_nodes"]
        for feed_name in required:
            assert feed_name in THREAT_FEEDS

    def test_get_feed(self):
        feed = get_feed("feodo_tracker")
        assert feed is not None
        assert feed.name == "feodo_tracker"
        assert feed.feed_type == FeedType.IP_LIST

    def test_get_feed_nonexistent(self):
        feed = get_feed("nonexistent")
        assert feed is None

    def test_get_enabled_feeds(self):
        enabled = get_enabled_feeds()
        assert len(enabled) > 0
        for name, feed in enabled.items():
            assert feed.enabled is True

    def test_get_ip_feeds(self):
        ip_feeds = get_ip_feeds()
        assert len(ip_feeds) > 0
        for feed_name in ip_feeds:
            feed = get_feed(feed_name)
            assert feed.feed_type == FeedType.IP_LIST


class TestSeverity:
    """Tests for severity calculations."""

    def test_severity_enum(self):
        assert Severity.CRITICAL.value == "critical"
        assert Severity.HIGH.value == "high"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.LOW.value == "low"

    def test_calculate_severity_critical(self):
        assert calculate_severity(90) == Severity.CRITICAL

    def test_calculate_severity_high(self):
        assert calculate_severity(60) == Severity.HIGH

    def test_calculate_severity_medium(self):
        assert calculate_severity(40) == Severity.MEDIUM

    def test_calculate_severity_low(self):
        assert calculate_severity(10) == Severity.LOW


class TestHelpers:
    """Tests for helper functions."""

    def test_get_timestamp_format(self):
        ts = get_timestamp()
        assert "T" in ts  # ISO format
        assert "-" in ts
