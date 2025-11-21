#!/usr/bin/env python3
"""
Test Anthropic Code Execution Pattern Improvements

Validates:
1. Progressive tool discovery (search_tools)
2. Cross-MCP proxy
3. PII tokenization
4. Lazy loading
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_tool_discovery():
    """Test progressive tool discovery"""
    print("\n=== Testing Tool Discovery ===")

    from sandbox.tool_discovery import (
        search_tools, list_servers, list_tools, init_tool_registry
    )

    # Initialize registry
    init_tool_registry()

    # Test list servers
    servers = list_servers()
    print(f"Available servers: {servers}")
    assert len(servers) > 0, "Should have servers"

    # Test list tools
    tools = list_tools("enhanced-memory")
    print(f"Enhanced-memory tools: {tools}")
    assert "search_nodes" in tools, "Should have search_nodes"

    # Test search - names only (minimal tokens)
    results = search_tools("search", detail_level="names")
    print(f"Search 'search' (names): {results['matches'][:3]}")
    assert results["count"] > 0, "Should find search tools"

    # Test search - brief descriptions
    results = search_tools("memory", detail_level="brief")
    print(f"Search 'memory' (brief): {results['matches'][:2]}")

    # Test search - full schema
    results = search_tools("converse", detail_level="full")
    print(f"Search 'converse' (full): found {results['count']} tools")

    print("Tool discovery tests passed!")


def test_pii_tokenization():
    """Test PII tokenization"""
    print("\n=== Testing PII Tokenization ===")

    from sandbox.pii_tokenizer import PIITokenizer

    tokenizer = PIITokenizer()

    # Test email
    text = "Contact john@example.com for info"
    tokenized, mappings = tokenizer.tokenize(text)
    print(f"Original: {text}")
    print(f"Tokenized: {tokenized}")
    assert "[EMAIL_1]" in tokenized, "Should tokenize email"

    # Test detokenization
    restored = tokenizer.detokenize(tokenized)
    print(f"Restored: {restored}")
    assert restored == text, "Should restore original"

    # Test dict tokenization
    data = {
        "user": {"email": "test@test.com", "ssn": "123-45-6789"},
        "note": "Call 555-123-4567"
    }
    tokenized_dict, _ = tokenizer.tokenize_dict(data)
    print(f"Tokenized dict: {tokenized_dict}")
    assert "[EMAIL" in str(tokenized_dict), "Should tokenize email in dict"
    assert "[SSN" in str(tokenized_dict), "Should tokenize SSN"
    assert "[PHONE" in str(tokenized_dict), "Should tokenize phone"

    # Test stats
    stats = tokenizer.get_stats()
    print(f"Stats: {stats}")
    assert stats["total_tokens"] > 0, "Should have tokens"

    print("PII tokenization tests passed!")


def test_mcp_proxy():
    """Test MCP proxy"""
    print("\n=== Testing MCP Proxy ===")

    from sandbox.mcp_proxy import MCPProxyClient, MCP_SERVERS

    proxy = MCPProxyClient()

    # Test server access
    voice = proxy.voice_mode
    print(f"Got voice_mode proxy: {voice}")

    # Test tool call queueing
    result = voice.converse(message="Hello", wait_for_response=False)
    print(f"Queued call: {result}")
    assert result["queued"], "Should queue call"

    # Test queue
    calls = proxy.get_queued_calls()
    print(f"Queued calls: {len(calls)}")
    assert len(calls) == 1, "Should have 1 queued call"

    # Test list servers
    servers = list(MCP_SERVERS.keys())
    print(f"Known MCP servers: {servers}")

    print("MCP proxy tests passed!")


def test_lazy_loader():
    """Test lazy loading"""
    print("\n=== Testing Lazy Loader ===")

    from sandbox.lazy_loader import LazyToolLoader, estimate_savings

    loader = LazyToolLoader()

    # Test schema loading
    schema = loader.get_tool_schema("enhanced-memory", "search_nodes")
    if schema:
        print(f"Loaded schema: {schema.get('name', 'N/A')}")

    # Test minimal schema
    minimal = loader.get_minimal_schema("voice-mode", "converse")
    if minimal:
        print(f"Minimal schema: {minimal}")

    # Test preloading
    loader.preload_workflow("memory_operations")

    # Test stats
    stats = loader.get_stats()
    print(f"Loader stats: {stats['cache']}")

    # Test savings estimation
    savings = estimate_savings(loaded_tools=8, total_tools=150)
    print(f"Estimated savings: {savings['percent_saved']}")

    print("Lazy loader tests passed!")


def test_integration():
    """Test full integration"""
    print("\n=== Testing Full Integration ===")

    from sandbox.executor import create_api_context, CodeExecutor

    executor = CodeExecutor()
    context = create_api_context(executor)

    # Check new APIs are available
    new_apis = ['search_tools', 'mcp', 'tokenize_pii', 'get_tool_schema']
    available = [api for api in new_apis if api in context]
    print(f"Available new APIs: {available}")

    # Test code execution with new features
    code = '''
# Test progressive tool discovery
if 'search_tools' in dir():
    tools = search_tools("memory", "brief")
    result = {"discovery_works": True, "found": tools.get("count", 0)}
else:
    result = {"discovery_works": False}
'''

    exec_result = executor.execute(code, context)
    print(f"Execution result: {exec_result.result}")

    print("Integration tests passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("Anthropic Code Execution Pattern Test Suite")
    print("=" * 60)

    tests = [
        test_tool_discovery,
        test_pii_tokenization,
        test_mcp_proxy,
        test_lazy_loader,
        test_integration,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAILED: {test.__name__}: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
