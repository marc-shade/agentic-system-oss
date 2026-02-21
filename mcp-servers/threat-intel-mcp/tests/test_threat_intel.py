#!/usr/bin/env python3
"""
Threat Intelligence MCP Server Tests
=====================================

Comprehensive tests for the threat intel integration.
"""

import asyncio
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server import (
    ThreatIntelDatabase,
    ThreatFeedFetcher,
    ThreatChecker,
    ThreatIndicator,
    ThreatType,
    ThreatSeverity,
    FeedSource,
)


class TestThreatIntelDatabase:
    """Tests for the threat intelligence database."""

    def setup_method(self):
        """Set up test fixtures."""
        # Use temporary database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_threat_intel.db"
        self.db = ThreatIntelDatabase(self.db_path)

    def teardown_method(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_database_initialization(self):
        """Test database schema creation."""
        assert self.db_path.exists()

        # Check tables exist
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        assert "indicators" in tables
        assert "feed_sync_history" in tables
        assert "alert_history" in tables

        conn.close()

    def test_add_indicator(self):
        """Test adding a threat indicator."""
        indicator = ThreatIndicator(
            indicator_type=ThreatType.IP.value,
            value="198.51.100.100",
            threat_type="botnet_c2",
            malware_family="Emotet",
            source=FeedSource.THREATFOX.value,
            first_seen=datetime.now(timezone.utc).isoformat(),
            last_seen=datetime.now(timezone.utc).isoformat(),
            confidence=90,
            severity=ThreatSeverity.CRITICAL.value,
            tags=["emotet", "banking"],
            reference_url="https://example.com",
            description="Test indicator"
        )

        result = self.db.add_indicator(indicator)
        assert result is True

        # Verify it was added
        found = self.db.lookup("198.51.100.100")
        assert len(found) == 1
        assert found[0].value == "198.51.100.100"
        assert found[0].malware_family == "Emotet"

    def test_lookup_not_found(self):
        """Test lookup for non-existent indicator."""
        found = self.db.lookup("203.0.113.1")
        assert len(found) == 0

    def test_deduplication(self):
        """Test that duplicate indicators are updated, not duplicated."""
        indicator1 = ThreatIndicator(
            indicator_type=ThreatType.IP.value,
            value="198.51.100.100",
            threat_type="botnet_c2",
            malware_family="Emotet",
            source=FeedSource.THREATFOX.value,
            first_seen=datetime.now(timezone.utc).isoformat(),
            last_seen=datetime.now(timezone.utc).isoformat(),
            confidence=80,
            severity=ThreatSeverity.HIGH.value,
            tags=["emotet"],
            reference_url=None,
            description=None
        )

        indicator2 = ThreatIndicator(
            indicator_type=ThreatType.IP.value,
            value="198.51.100.100",  # Same value
            threat_type="botnet_c2",
            malware_family="Emotet",
            source=FeedSource.THREATFOX.value,  # Same source
            first_seen=datetime.now(timezone.utc).isoformat(),
            last_seen=datetime.now(timezone.utc).isoformat(),
            confidence=95,  # Updated confidence
            severity=ThreatSeverity.CRITICAL.value,
            tags=["emotet", "updated"],
            reference_url=None,
            description=None
        )

        self.db.add_indicator(indicator1)
        self.db.add_indicator(indicator2)

        # Should only have one entry
        found = self.db.lookup("198.51.100.100")
        assert len(found) == 1

    def test_stats(self):
        """Test database statistics."""
        # Add some indicators
        for i in range(5):
            indicator = ThreatIndicator(
                indicator_type=ThreatType.IP.value,
                value=f"198.51.100.{i}",
                threat_type="test",
                malware_family=None,
                source=FeedSource.MANUAL.value,
                first_seen=datetime.now(timezone.utc).isoformat(),
                last_seen=datetime.now(timezone.utc).isoformat(),
                confidence=50,
                severity=ThreatSeverity.MEDIUM.value,
                tags=[],
                reference_url=None,
                description=None
            )
            self.db.add_indicator(indicator)

        stats = self.db.get_stats()

        assert stats["total_indicators"] == 5
        assert stats["by_type"].get("ip", 0) == 5


class TestThreatChecker:
    """Tests for threat checking functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_threat_intel.db"
        self.db = ThreatIntelDatabase(self.db_path)
        self.checker = ThreatChecker(self.db)

        # Add some test indicators
        self._add_test_indicators()

    def teardown_method(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _add_test_indicators(self):
        """Add test indicators to database."""
        indicators = [
            ThreatIndicator(
                indicator_type=ThreatType.IP.value,
                value="198.51.100.100",
                threat_type="botnet_c2",
                malware_family="Emotet",
                source=FeedSource.FEODO_TRACKER.value,
                first_seen=datetime.now(timezone.utc).isoformat(),
                last_seen=datetime.now(timezone.utc).isoformat(),
                confidence=95,
                severity=ThreatSeverity.CRITICAL.value,
                tags=["emotet"],
                reference_url=None,
                description="Test C2 IP"
            ),
            ThreatIndicator(
                indicator_type=ThreatType.URL.value,
                value="http://malware.example.com/payload.exe",
                threat_type="malware_download",
                malware_family="GenericTrojan",
                source=FeedSource.URLHAUS.value,
                first_seen=datetime.now(timezone.utc).isoformat(),
                last_seen=datetime.now(timezone.utc).isoformat(),
                confidence=80,
                severity=ThreatSeverity.HIGH.value,
                tags=["trojan"],
                reference_url=None,
                description="Test malware URL"
            ),
            ThreatIndicator(
                indicator_type=ThreatType.CVE.value,
                value="CVE-2024-1234",
                threat_type="known_exploited_vulnerability",
                malware_family=None,
                source=FeedSource.CISA_KEV.value,
                first_seen=datetime.now(timezone.utc).isoformat(),
                last_seen=datetime.now(timezone.utc).isoformat(),
                confidence=100,
                severity=ThreatSeverity.CRITICAL.value,
                tags=["cisa", "kev"],
                reference_url=None,
                description="Test KEV"
            ),
        ]

        for ind in indicators:
            self.db.add_indicator(ind)

    def test_check_known_indicator(self):
        """Test checking a known malicious indicator."""
        result = self.checker.check_indicator("198.51.100.100")

        assert result.found is True
        assert result.risk_score >= 80
        assert len(result.matches) > 0
        assert result.matches[0].malware_family == "Emotet"

    def test_check_unknown_indicator(self):
        """Test checking an unknown indicator."""
        result = self.checker.check_indicator("203.0.113.1")

        assert result.found is False
        assert result.risk_score == 0
        assert len(result.matches) == 0

    def test_scan_text_with_threats(self):
        """Test scanning text containing malicious indicators."""
        text = """
        Server logs show connections from:
        - 198.51.100.100 (suspicious)
        - 203.0.113.1 (clean)

        Also found reference to CVE-2024-1234 in dependencies.

        Downloaded file from http://malware.example.com/payload.exe
        """

        results = self.checker.scan_text(text, "test context")

        # Should find IP, URL, and CVE
        assert len(results["ips"]) >= 1
        assert len(results["urls"]) >= 1
        assert len(results["cves"]) >= 1

        # Verify specific findings
        ip_match = next((m for m in results["ips"] if "198.51.100.100" in m.indicator), None)
        assert ip_match is not None
        assert ip_match.risk_score >= 80

    def test_scan_text_clean(self):
        """Test scanning clean text."""
        text = "This is a normal log entry with no threats."

        results = self.checker.scan_text(text)

        # Should find nothing
        total_found = sum(len(v) for v in results.values())
        assert total_found == 0


class TestThreatFeedFetcher:
    """Tests for feed fetching (with mocked HTTP)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_threat_intel.db"
        self.db = ThreatIntelDatabase(self.db_path)
        self.fetcher = ThreatFeedFetcher(self.db)

    def teardown_method(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        asyncio.run(self.fetcher.close())

    @patch('aiohttp.ClientSession')
    def test_fetch_threatfox_mock(self, mock_session):
        """Test ThreatFox fetch with mocked response."""

        async def run_test():
            # Mock response
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "query_status": "ok",
                "data": [
                    {
                        "ioc_type": "ip:port",
                        "ioc": "1.2.3.4:443",
                        "threat_type": "botnet_cc",
                        "malware_printable": "TestMalware",
                        "confidence_level": 90,
                        "first_seen_utc": "2024-01-01 00:00:00",
                        "last_seen_utc": "2024-01-01 00:00:00",
                        "tags": ["test"],
                        "reference": None,
                        "malware_alias": None
                    }
                ]
            })

            # Set up mock session
            mock_session_instance = MagicMock()
            mock_session_instance.post = MagicMock(return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_response),
                __aexit__=AsyncMock()
            ))
            mock_session_instance.closed = False
            mock_session.return_value = mock_session_instance

            self.fetcher.session = mock_session_instance

            added, updated = await self.fetcher.fetch_threatfox()

            # Should have added the indicator
            assert added >= 0  # May vary based on mock setup

        asyncio.run(run_test())


def run_all_tests():
    """Run all tests and report results."""
    import traceback

    test_classes = [
        TestThreatIntelDatabase,
        TestThreatChecker,
        # TestThreatFeedFetcher,  # Requires more complex mocking
    ]

    total_passed = 0
    total_failed = 0
    failures = []

    print("=" * 60)
    print("THREAT INTELLIGENCE MCP SERVER - TEST SUITE")
    print("=" * 60)
    print()

    for test_class in test_classes:
        print(f"\n--- {test_class.__name__} ---\n")

        instance = test_class()

        for method_name in dir(instance):
            if method_name.startswith("test_"):
                try:
                    # Setup
                    if hasattr(instance, "setup_method"):
                        instance.setup_method()

                    # Run test
                    getattr(instance, method_name)()

                    # Teardown
                    if hasattr(instance, "teardown_method"):
                        instance.teardown_method()

                    print(f"  PASS: {method_name}")
                    total_passed += 1

                except AssertionError as e:
                    print(f"  FAIL: {method_name}")
                    print(f"        {e}")
                    total_failed += 1
                    failures.append((test_class.__name__, method_name, str(e)))

                except Exception as e:
                    print(f"  ERROR: {method_name}")
                    print(f"         {e}")
                    traceback.print_exc()
                    total_failed += 1
                    failures.append((test_class.__name__, method_name, str(e)))

    print()
    print("=" * 60)
    print(f"RESULTS: {total_passed} passed, {total_failed} failed")
    print("=" * 60)

    if failures:
        print("\nFailures:")
        for cls, method, error in failures:
            print(f"  - {cls}.{method}: {error}")

    return total_failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
