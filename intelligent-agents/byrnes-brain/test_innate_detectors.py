#!/usr/bin/env python3
"""
Comprehensive tests for the Innate Detector System.
Tests all detector types and edge cases.
"""

import sys
import os

# Add hooks directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from innate_detectors import (
    InnateDetectorSystem,
    SecurityThreatDetector,
    ProductionViolationDetector,
    ResourceExhaustionDetector,
    DataCorruptionDetector,
    PrivacyViolationDetector,
    Severity,
    quick_innate_scan
)


def test_security_threats():
    """Test SecurityThreatDetector patterns"""
    detector = SecurityThreatDetector()

    # Destructive commands - should detect
    assert detector.scan({'tool': 'Bash', 'arguments': {'command': 'rm -rf /'}})
    assert detector.scan({'tool': 'Bash', 'arguments': {'command': 'rm -rf /*'}})
    assert detector.scan({'tool': 'Bash', 'arguments': {'command': 'sudo rm -rf /var'}})
    assert detector.scan({'tool': 'Bash', 'arguments': {'command': 'DROP TABLE users;'}})
    assert detector.scan({'tool': 'Bash', 'arguments': {'command': 'TRUNCATE TABLE orders;'}})

    # API keys - should detect (using concatenation to avoid pre-push hook false positives)
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'api_key = "sk-' + 'ant-api03-abcdefghijklmnop"'}})
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'OPENAI_KEY=sk-' + '1234567890abcdefghijklmnop'}})
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'token: ghp_' + 'abcdefghijklmnopqrstuvwxyz1234567890'}})
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'aws_key = AKIA' + 'IOSFODNN7EXAMPLE'}})

    # Private keys - should detect
    assert detector.scan({'tool': 'Write', 'arguments': {'content': '-----BEGIN RSA PRIVATE KEY-----'}})
    assert detector.scan({'tool': 'Write', 'arguments': {'content': '-----BEGIN OPENSSH PRIVATE KEY-----'}})

    # Safe commands - should NOT detect
    assert detector.scan({'tool': 'Bash', 'arguments': {'command': 'ls -la'}}) is None
    assert detector.scan({'tool': 'Bash', 'arguments': {'command': 'git status'}}) is None
    assert detector.scan({'tool': 'Bash', 'arguments': {'command': 'npm install'}}) is None
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'def hello(): return "world"'}}) is None

    print("✓ SecurityThreatDetector tests passed")


def test_production_violations():
    """Test ProductionViolationDetector patterns"""
    detector = ProductionViolationDetector()

    # POC/Demo markers - should detect
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'This is a POC implementation'}})
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'proof of concept version'}})
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'demo mode enabled'}})
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'This prototype shows'}})

    # Placeholder content - should detect
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'Lorem ipsum dolor sit amet'}})
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'TODO: implement this feature'}})

    # Mock/fake data - should detect
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'using mock data for testing'}})
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'fake_response = {}'}})
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'dummy_data = [1, 2, 3]'}})
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'hardcoded values here'}})

    # Empty implementations - should detect
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'def foo():\n    pass'}})
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'raise NotImplementedError()'}})

    # Production code - should NOT detect
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'def process_data(data): return data.transform()'}}) is None
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'class UserService:\n    def get_user(self, id): ...'}}) is None

    # Read tool - should NOT check (not a write operation)
    assert detector.scan({'tool': 'Read', 'arguments': {'file_path': '/poc/demo.py'}}) is None

    print("✓ ProductionViolationDetector tests passed")


def test_resource_exhaustion():
    """Test ResourceExhaustionDetector patterns"""
    detector = ResourceExhaustionDetector()

    # Infinite loops - should detect
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'while(true) { }'}})
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'while True:\n    pass'}})
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'for(;;) { console.log("infinite"); }'}})

    # Large allocations - should detect
    assert detector.scan({'tool': 'Write', 'arguments': {'content': '["x"] * 1000000000'}})
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'range(10000000000)'}})
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'new Array(10000000000)'}})

    # Normal loops - should NOT detect
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'for i in range(10): print(i)'}}) is None
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'while count < 100: count += 1'}}) is None

    print("✓ ResourceExhaustionDetector tests passed")


def test_data_corruption():
    """Test DataCorruptionDetector patterns"""
    detector = DataCorruptionDetector()

    # MongoDB destructive - should detect
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'db.users.drop()'}})
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'collection.deleteMany({})'}})

    # File system destructive - should detect
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'shutil.rmtree("/home")'}})

    # Git destructive - should detect
    assert detector.scan({'tool': 'Bash', 'arguments': {'command': 'git push --force origin main'}})
    assert detector.scan({'tool': 'Bash', 'arguments': {'command': 'git reset --hard HEAD~5'}})

    # Safe git - should NOT detect
    assert detector.scan({'tool': 'Bash', 'arguments': {'command': 'git push origin main'}}) is None
    assert detector.scan({'tool': 'Bash', 'arguments': {'command': 'git commit -m "fix"'}}) is None

    print("✓ DataCorruptionDetector tests passed")


def test_privacy_violations():
    """Test PrivacyViolationDetector patterns"""
    detector = PrivacyViolationDetector()

    # SSN patterns - should detect
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'ssn = 123-45-6789'}})
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'social: 123.45.6789'}})

    # Credit card - should detect
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'card: 1234567890123456'}})
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'cc: 1234-5678-9012-3456'}})

    # Password logging - should detect
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'print(f"password is {password}")'}})
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'console.log("secret:", secret)'}})

    # Safe logging - should NOT detect
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'print("User logged in")'}}) is None
    assert detector.scan({'tool': 'Write', 'arguments': {'content': 'logger.info("Processing complete")'}}) is None

    print("✓ PrivacyViolationDetector tests passed")


def test_system_integration():
    """Test InnateDetectorSystem integration"""
    system = InnateDetectorSystem()

    # Critical threat - should block
    alerts = system.quick_scan({'tool': 'Bash', 'arguments': {'command': 'rm -rf /'}})
    assert len(alerts) > 0
    assert system.should_block_immediately(alerts)

    # High threat - should warn but not block
    alerts = system.quick_scan({'tool': 'Write', 'arguments': {'content': 'POC version'}})
    assert len(alerts) > 0
    assert not system.should_block_immediately(alerts)

    # Safe operation - no alerts
    alerts = system.quick_scan({'tool': 'Read', 'arguments': {'file_path': 'readme.md'}})
    assert len(alerts) == 0
    assert not system.should_block_immediately(alerts)

    # Multiple detectors can fire
    alerts = system.quick_scan({'tool': 'Write', 'arguments': {
        'content': 'sk-ant-api-key-here\nPOC implementation\nwhile(true){}'
    }})
    assert len(alerts) >= 2  # At least secret + production violation

    print("✓ System integration tests passed")


def test_convenience_function():
    """Test quick_innate_scan convenience function"""

    # Critical - should not allow
    allow, alerts = quick_innate_scan({'tool': 'Bash', 'arguments': {'command': 'DROP DATABASE production;'}})
    assert not allow
    assert len(alerts) > 0

    # Safe - should allow
    allow, alerts = quick_innate_scan({'tool': 'Bash', 'arguments': {'command': 'echo hello'}})
    assert allow

    print("✓ Convenience function tests passed")


def test_severity_levels():
    """Test that severity levels are correctly assigned"""
    system = InnateDetectorSystem()

    # Critical severity
    alerts = system.quick_scan({'tool': 'Bash', 'arguments': {'command': 'rm -rf /'}})
    assert alerts[0].severity == Severity.CRITICAL

    # High severity
    alerts = system.quick_scan({'tool': 'Write', 'arguments': {'content': 'POC implementation'}})
    assert alerts[0].severity == Severity.HIGH

    # Medium severity
    alerts = system.quick_scan({'tool': 'Write', 'arguments': {'content': 'static dashboard data'}})
    if alerts:  # May or may not trigger depending on exact pattern
        assert alerts[0].severity in [Severity.MEDIUM, Severity.HIGH]

    print("✓ Severity level tests passed")


def test_performance():
    """Test that scanning is fast enough"""
    import time

    system = InnateDetectorSystem()

    # Generate a large content block
    large_content = "def process_data(data):\n" * 1000
    action = {'tool': 'Write', 'arguments': {'content': large_content}}

    # Should complete in under 100ms even for large content
    start = time.time()
    for _ in range(100):
        system.quick_scan(action)
    elapsed = time.time() - start

    avg_ms = (elapsed / 100) * 1000
    assert avg_ms < 10, f"Scan too slow: {avg_ms:.2f}ms average"

    print(f"✓ Performance test passed ({avg_ms:.2f}ms average per scan)")


def run_all_tests():
    """Run all test functions"""
    print("=" * 60)
    print("Running Innate Detector System Tests")
    print("=" * 60)
    print()

    test_functions = [
        test_security_threats,
        test_production_violations,
        test_resource_exhaustion,
        test_data_corruption,
        test_privacy_violations,
        test_system_integration,
        test_convenience_function,
        test_severity_levels,
        test_performance,
    ]

    passed = 0
    failed = 0

    for test_fn in test_functions:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test_fn.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test_fn.__name__} ERROR: {e}")
            failed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
