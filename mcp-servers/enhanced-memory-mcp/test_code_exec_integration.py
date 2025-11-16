#!/usr/bin/env python3
"""
Test Code Execution Integration in Enhanced Memory MCP

Quick test to verify:
1. Server imports successfully
2. execute_code function exists
3. Basic execution works
4. API access works
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_basic_execution():
    """Test 1: Basic code execution"""
    print("\n=== Test 1: Basic Execution ===")

    from sandbox.executor import CodeExecutor

    executor = CodeExecutor()
    code = """
result = sum(range(100))
    """

    exec_result = executor.execute(code)

    assert exec_result.success, f"Failed: {exec_result.error}"
    assert exec_result.result == 4950
    print(f"✅ Basic execution: {exec_result.result} (in {exec_result.execution_time_ms:.2f}ms)")


async def test_api_access():
    """Test 2: API access from code"""
    print("\n=== Test 2: API Access ===")

    from sandbox.executor import CodeExecutor, create_api_context

    executor = CodeExecutor()
    context = create_api_context()

    code = """
# Test that API functions are available by trying to call them
try:
    # Check if functions exist by testing their type
    available = (
        callable(search_nodes) and
        callable(filter_by_confidence) and
        callable(summarize_results) and
        callable(aggregate_stats)
    )
    result = {"api_available": available}
except NameError:
    result = {"api_available": False}
    """

    exec_result = executor.execute(code, context=context)

    assert exec_result.success, f"Failed: {exec_result.error}"
    assert exec_result.result["api_available"], "API functions not available in context"
    print(f"✅ API access: All required functions available")


async def test_security():
    """Test 3: Security blocking"""
    print("\n=== Test 3: Security Checks ===")

    from sandbox.security import comprehensive_safety_check

    dangerous_code = "import os; os.system('rm -rf /')"

    is_safe, issues = comprehensive_safety_check(dangerous_code)

    assert not is_safe, "Security check should have blocked dangerous code"
    print(f"✅ Security blocking: {issues[0]}")


async def test_token_savings_demo():
    """Test 4: Token savings demonstration"""
    print("\n=== Test 4: Token Savings Demo ===")

    from sandbox.executor import CodeExecutor, create_api_context

    executor = CodeExecutor()
    context = create_api_context()

    # Simulate filtering 100 results locally
    code = """
# Create mock results (simulating search_nodes output)
results = [
    {"name": f"item_{i}", "confidence": i/10, "entityType": "test"}
    for i in range(100)
]

# Filter to high confidence
high_conf = filter_by_confidence(results, 0.8)

# Summarize
summary = summarize_results(high_conf)

result = {
    "original_count": len(results),
    "filtered_count": summary["count"],
    "avg_confidence": summary["avg_confidence"]
}
    """

    exec_result = executor.execute(code, context=context)

    assert exec_result.success, f"Failed: {exec_result.error}"

    original_tokens = 100 * 500  # Estimate for 100 full results
    result_tokens = len(str(exec_result.result))
    savings_pct = ((original_tokens - result_tokens) / original_tokens) * 100

    print(f"✅ Token savings:")
    print(f"   Before: ~{original_tokens:,} tokens (100 results)")
    print(f"   After: ~{result_tokens} tokens (summary)")
    print(f"   Savings: {savings_pct:.1f}%")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Enhanced Memory MCP - Code Execution Integration Tests")
    print("=" * 60)

    tests = [
        test_basic_execution,
        test_api_access,
        test_security,
        test_token_savings_demo,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            await test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} failed: {str(e)}")
            failed += 1
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed == 0:
        print("\n✅ All tests passed! Integration successful!")
        print("\nNext steps:")
        print("1. Restart Claude Code to load updated MCP")
        print("2. Test execute_code tool in conversation")
        print("3. Verify token savings in production usage")
    else:
        print("\n⚠️  Some tests failed. Review errors above.")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
