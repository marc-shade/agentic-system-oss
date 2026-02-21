"""
Tests for threat_intel_mcp.server module.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from threat_intel_mcp.server import (
    parse_ip_list,
    parse_url_list,
    parse_cidr_list,
    fetch_url,
    fetch_json,
)


class TestParseIPList:
    """Tests for IP list parsing."""

    def test_parse_simple_list(self):
        content = """198.51.100.1
203.0.113.1
8.8.8.8"""
        ips = parse_ip_list(content)
        assert len(ips) == 3
        assert "198.51.100.1" in ips
        assert "203.0.113.1" in ips

    def test_parse_with_comments(self):
        content = """# This is a comment
198.51.100.1
# Another comment
203.0.113.1"""
        ips = parse_ip_list(content)
        assert len(ips) == 2

    def test_parse_empty_lines(self):
        content = """198.51.100.1

203.0.113.1

8.8.8.8"""
        ips = parse_ip_list(content)
        assert len(ips) == 3

    def test_parse_invalid_ips_filtered(self):
        content = """198.51.100.1
invalid-ip
256.1.1.1
203.0.113.1"""
        ips = parse_ip_list(content)
        assert len(ips) == 2
        assert "invalid-ip" not in ips
        assert "256.1.1.1" not in ips

    def test_parse_ip_with_trailing_content(self):
        content = """198.51.100.1 some comment
203.0.113.1\tmore data"""
        ips = parse_ip_list(content)
        assert len(ips) == 2


class TestParseURLList:
    """Tests for URL list parsing."""

    def test_parse_simple_urls(self):
        content = """http://example.com/malware
https://phishing.com/login"""
        urls = parse_url_list(content)
        assert len(urls) == 2

    def test_parse_with_comments(self):
        content = """# Malware URLs
http://malware.com/payload
# Phishing
https://phish.com"""
        urls = parse_url_list(content)
        assert len(urls) == 2

    def test_ignore_non_http_urls(self):
        content = """http://valid.com
ftp://invalid.com
https://also-valid.com
file:///local"""
        urls = parse_url_list(content)
        assert len(urls) == 2


class TestParseCIDRList:
    """Tests for CIDR list parsing."""

    def test_parse_cidr_ranges(self):
        content = """192.168.0.0/24
203.0.113.0/8"""
        cidrs = parse_cidr_list(content)
        assert len(cidrs) == 2

    def test_parse_with_semicolon_comments(self):
        content = """; Spamhaus DROP list
192.168.0.0/16
; Another block
203.0.113.0/8"""
        cidrs = parse_cidr_list(content)
        assert len(cidrs) == 2

    def test_parse_invalid_cidr_filtered(self):
        content = """192.168.0.0/24
invalid/cidr
203.0.113.0/8"""
        cidrs = parse_cidr_list(content)
        assert len(cidrs) == 2


def get_fn(tool):
    """Extract the underlying function from a FastMCP tool."""
    # FastMCP wraps functions - get the original
    if hasattr(tool, 'fn'):
        return tool.fn
    if hasattr(tool, '__wrapped__'):
        return tool.__wrapped__
    return tool


class TestServerToolsWithMocks:
    """Integration tests for MCP tools using mocks."""

    @pytest.mark.asyncio
    async def test_get_threat_feeds(self):
        """Test get_threat_feeds returns proper structure."""
        from threat_intel_mcp.server import get_threat_feeds

        fn = get_fn(get_threat_feeds)
        result = await fn()
        data = json.loads(result)

        assert data["success"] is True
        assert "feeds" in data
        assert "total_feeds" in data
        assert "api_configured" in data
        assert len(data["feeds"]) > 0

    @pytest.mark.asyncio
    async def test_check_ip_reputation_invalid_ip(self):
        """Test check_ip_reputation with invalid IP."""
        from threat_intel_mcp.server import check_ip_reputation

        fn = get_fn(check_ip_reputation)
        result = await fn("invalid-ip")
        data = json.loads(result)

        assert data["success"] is False
        assert "error" in data

    @pytest.mark.asyncio
    async def test_check_ip_reputation_valid_ip(self, clean_cache):
        """Test check_ip_reputation with valid IP."""
        from threat_intel_mcp.server import check_ip_reputation

        fn = get_fn(check_ip_reputation)
        result = await fn("8.8.8.8")
        data = json.loads(result)

        assert data["success"] is True
        assert data["ip"] == "8.8.8.8"
        assert "threats_found" in data
        assert "sources_checked" in data
        assert "threat_level" in data

    @pytest.mark.asyncio
    async def test_check_hash_reputation_invalid_hash(self):
        """Test check_hash_reputation with invalid hash."""
        from threat_intel_mcp.server import check_hash_reputation

        fn = get_fn(check_hash_reputation)
        result = await fn("invalid")
        data = json.loads(result)

        assert data["success"] is False
        assert "error" in data

    @pytest.mark.asyncio
    async def test_check_hash_reputation_valid_md5(self):
        """Test check_hash_reputation with valid MD5."""
        from threat_intel_mcp.server import check_hash_reputation

        fn = get_fn(check_hash_reputation)
        result = await fn("d41d8cd98f00b204e9800998ecf8427e")
        data = json.loads(result)

        assert data["success"] is True
        assert data["hash_type"] == "md5"

    @pytest.mark.asyncio
    async def test_check_bulk_ips_comma_separated(self, clean_cache):
        """Test bulk IP checking with comma-separated list."""
        from threat_intel_mcp.server import check_bulk_ips

        fn = get_fn(check_bulk_ips)
        result = await fn("8.8.8.8, 1.1.1.1, 198.51.100.1")
        data = json.loads(result)

        assert data["success"] is True
        assert data["total_checked"] == 3

    @pytest.mark.asyncio
    async def test_check_bulk_ips_json_array(self, clean_cache):
        """Test bulk IP checking with JSON array."""
        from threat_intel_mcp.server import check_bulk_ips

        fn = get_fn(check_bulk_ips)
        result = await fn('["8.8.8.8", "1.1.1.1"]')
        data = json.loads(result)

        assert data["success"] is True
        assert data["total_checked"] == 2

    @pytest.mark.asyncio
    async def test_check_bulk_ips_too_many(self):
        """Test bulk IP checking rejects too many IPs."""
        from threat_intel_mcp.server import check_bulk_ips

        fn = get_fn(check_bulk_ips)
        # Create list of 101 IPs
        ips = ",".join([f"198.51.100.{i}" for i in range(101)])
        result = await fn(ips)
        data = json.loads(result)

        assert data["success"] is False
        assert "Maximum 100" in data["error"]

    @pytest.mark.asyncio
    async def test_get_recent_iocs_invalid_type(self):
        """Test get_recent_iocs with invalid IOC type."""
        from threat_intel_mcp.server import get_recent_iocs

        fn = get_fn(get_recent_iocs)
        result = await fn(ioc_type="invalid")
        data = json.loads(result)

        assert data["success"] is False
        assert "Invalid IOC type" in data["error"]

    @pytest.mark.asyncio
    async def test_get_threat_stats(self, clean_cache):
        """Test get_threat_stats returns proper structure."""
        from threat_intel_mcp.server import get_threat_stats

        fn = get_fn(get_threat_stats)
        result = await fn()
        data = json.loads(result)

        assert data["success"] is True
        assert "cache" in data
        assert "feeds_configured" in data
        assert "api_keys" in data

    @pytest.mark.asyncio
    async def test_clear_threat_cache(self, clean_cache):
        """Test clear_threat_cache works correctly."""
        from threat_intel_mcp.server import clear_threat_cache
        from threat_intel_mcp.config import threat_cache

        # Add something to cache
        threat_cache.set("test", "value")
        assert threat_cache.get("test") == "value"

        # Clear cache
        fn = get_fn(clear_threat_cache)
        result = await fn()
        data = json.loads(result)

        assert data["success"] is True
        assert threat_cache.get("test") is None

    @pytest.mark.asyncio
    async def test_check_network_against_threats_invalid_json(self):
        """Test check_network_against_threats with invalid JSON."""
        from threat_intel_mcp.server import check_network_against_threats

        fn = get_fn(check_network_against_threats)
        result = await fn("not valid json")
        data = json.loads(result)

        assert data["success"] is False
        assert "Invalid JSON" in data["error"]

    @pytest.mark.asyncio
    async def test_check_network_against_threats_no_devices(self):
        """Test check_network_against_threats with no devices."""
        from threat_intel_mcp.server import check_network_against_threats

        fn = get_fn(check_network_against_threats)
        result = await fn('{"devices": []}')
        data = json.loads(result)

        assert data["success"] is False
        assert "No devices" in data["error"]

    @pytest.mark.asyncio
    async def test_fetch_threat_feed_unknown_feed(self):
        """Test fetch_threat_feed with unknown feed name."""
        from threat_intel_mcp.server import fetch_threat_feed

        fn = get_fn(fetch_threat_feed)
        result = await fn("nonexistent_feed")
        data = json.loads(result)

        assert data["success"] is False
        assert "Unknown feed" in data["error"]
        assert "available_feeds" in data
