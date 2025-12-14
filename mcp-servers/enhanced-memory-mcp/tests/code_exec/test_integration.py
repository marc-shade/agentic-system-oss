#!/usr/bin/env python3
"""
Integration Tests for Code Execution Pattern

Tests end-to-end functionality:
1. Code execution in sandbox
2. API access from executed code
3. Security validation
4. Token savings
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sandbox.executor import CodeExecutor, create_api_context
from sandbox.security import comprehensive_safety_check, sanitize_output


def test_basic_execution():
    """Test basic code execution"""
    print("\n=== Test 1: Basic Execution ===")

    executor = CodeExecutor()

    code = """
result = sum(range(100))
result = result
    """

    result = executor.execute(code)

    assert result.success, f"Execution failed: {result.error}"
    assert result.result == 4950, f"Expected 4950, got {result.result}"

    print(f"✅ Basic execution: {result.result}")
    print(f"   Execution time: {result.execution_time_ms:.2f}ms")


def test_api_access():
    """Test API access from executed code"""
    print("\n=== Test 2: API Access ===")

    executor = CodeExecutor()
    context = create_api_context()

    code = """
status = get_status()
result = {
    "entity_count": status.get("entity_count", 0),
    "test": "api_access_works"
}
    """

    result = executor.execute(code, context=context)

    assert result.success, f"Execution failed: {result.error}"
    assert "test" in result.result, "Result missing expected fields"
    assert result.result["test"] == "api_access_works"

    print(f"✅ API access: {result.result}")
    print(f"   Execution time: {result.execution_time_ms:.2f}ms")


def test_security_blocking():
    """Test security checks block dangerous code"""
    print("\n=== Test 3: Security Blocking ===")

    dangerous_codes = [
        ("import os", "Dangerous import"),
        ("eval('1+1')", "eval() usage"),
        ("open('/etc/passwd')", "File access"),
    ]

    for code, description in dangerous_codes:
        is_safe, issues = comprehensive_safety_check(code)
        assert not is_safe, f"Security check should have blocked: {description}"
        print(f"✅ Blocked: {description}")


def test_timeout():
    """Test timeout enforcement"""
    print("\n=== Test 4: Timeout Enforcement ===")

    executor = CodeExecutor(timeout_seconds=2)

    code = """
import time
time.sleep(10)
result = "should timeout"
    """

    result = executor.execute(code)

    assert not result.success, "Should have timed out"
    assert "Timeout" in result.error or "time" in result.error.lower()

    print(f"✅ Timeout enforced: {result.error}")


def test_token_savings():
    """Test token savings through local filtering"""
    print("\n=== Test 5: Token Savings ===")

    executor = CodeExecutor()
    context = create_api_context()

    code = """
results = [
    {"name": f"item_{i}", "confidence": i/10, "entityType": "test"}
    for i in range(100)
]

high_conf = filter_by_confidence(results, 0.8)

summary = summarize_results(high_conf)

result = {
    "filtered_count": summary["count"],
    "avg_confidence": summary["avg_confidence"]
}
    """

    result = executor.execute(code, context=context)

    assert result.success, f"Execution failed: {result.error}"
    assert result.result["filtered_count"] == 20
    assert result.result["avg_confidence"] > 0.8

    before_tokens = 100 * 500
    after_tokens = len(str(result.result))
    savings_pct = ((before_tokens - after_tokens) / before_tokens) * 100

    print(f"✅ Token savings demonstration:")
    print(f"   Before: ~{before_tokens:,} tokens (100 full results)")
    print(f"   After: ~{after_tokens} tokens (summary only)")
    print(f"   Savings: {savings_pct:.1f}%")


def test_pii_tokenization():
    """Test PII tokenization in output"""
    print("\n=== Test 6: PII Tokenization ===")

    executor = CodeExecutor()

    code = """
data = {
    "email": "user@example.com",
    "ssn": "123-45-6789",
    "phone": "555-123-4567"
}
result = data
    """

    result = executor.execute(code)

    sanitized = sanitize_output(result.result)

    assert "[EMAIL]" in str(sanitized.values())
    assert "[SSN]" in str(sanitized.values())
    assert "[PHONE]" in str(sanitized.values())

    print(f"✅ PII tokenization:")
    print(f"   Original: {result.result}")
    print(f"   Sanitized: {sanitized}")


def test_error_handling():
    """Test error handling in executed code"""
    print("\n=== Test 7: Error Handling ===")

    executor = CodeExecutor()

    code = """
result = 1 / 0
result = result
    """

    result = executor.execute(code)

    assert not result.success, "Should have failed with division by zero"
    assert "ZeroDivisionError" in result.error

    print(f"✅ Error handled: {result.error}")


def run_all_tests():
    """Run all integration tests"""
    print("=" * 60)
    print("Enhanced Memory MCP - Code Execution Integration Tests")
    print("=" * 60)

    tests = [
        test_basic_execution,
        test_api_access,
        test_security_blocking,
        test_timeout,
        test_token_savings,
        test_pii_tokenization,
        test_error_handling,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} failed: {str(e)}")
            failed += 1
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
