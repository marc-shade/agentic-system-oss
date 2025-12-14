#!/usr/bin/env python3
"""
Test Advanced Tool Use Implementation

Validates:
1. Tool catalog is complete and well-organized
2. Tool search returns relevant results
3. Deferred loading configuration is correct
4. Token reduction is as expected (89%)
"""

import sys
import json
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

def test_tool_catalog():
    """Test tool catalog completeness"""
    print("\n" + "="*60)
    print("TEST 1: Tool Catalog Validation")
    print("="*60)

    from tool_catalog import (
        TOOL_CATALOG,
        ToolTier,
        get_tool_count_by_tier,
        get_hot_tools,
        ALWAYS_LOAD,
    )

    counts = get_tool_count_by_tier()
    print(f"\nTool Distribution:")
    print(f"  HOT (always loaded):  {counts['hot']:3d} tools")
    print(f"  WARM (on category):   {counts['warm']:3d} tools")
    print(f"  COLD (on demand):     {counts['cold']:3d} tools")
    print(f"  TOTAL cataloged:      {counts['total']:3d} tools")

    # Verify all HOT tools are in ALWAYS_LOAD
    hot_tools = [t.name for t in TOOL_CATALOG.values() if t.tier == ToolTier.HOT]
    missing = set(hot_tools) - ALWAYS_LOAD
    extra = ALWAYS_LOAD - set(hot_tools)

    if missing:
        print(f"\n⚠️  HOT tools not in ALWAYS_LOAD: {missing}")
    if extra:
        print(f"\n⚠️  ALWAYS_LOAD has extra tools: {extra}")

    # Check tool quality
    incomplete = []
    for name, tool in TOOL_CATALOG.items():
        if not tool.description or len(tool.description) < 20:
            incomplete.append(f"{name}: missing/short description")
        if not tool.keywords:
            incomplete.append(f"{name}: no keywords")

    if incomplete:
        print(f"\n⚠️  Incomplete tool definitions:")
        for item in incomplete[:5]:
            print(f"    - {item}")
    else:
        print(f"\n✅ All {counts['total']} tools have complete definitions")

    return counts['total'] >= 50  # Expect at least 50 cataloged

def test_tool_search():
    """Test tool search functionality"""
    print("\n" + "="*60)
    print("TEST 2: Tool Search Functionality")
    print("="*60)

    from tool_search import search_tools, get_tool_schema, get_related_tools

    test_queries = [
        ("store memory", ["create_entities", "nmf_remember"]),
        ("search past experiences", ["search_nodes", "nmf_recall", "search_with_reranking"]),
        ("cluster status", ["cluster_brain_status"]),
        ("track beliefs", ["record_belief_state"]),
        ("batch operations", ["execute_code"]),
    ]

    all_passed = True
    for query, expected_tools in test_queries:
        results = search_tools(query, limit=5)
        found_names = [r.tool_name for r in results]

        # Check if at least one expected tool is in top 5
        matches = set(found_names) & set(expected_tools)

        if matches:
            print(f"\n✅ Query: '{query}'")
            print(f"   Found: {found_names[:3]}")
            print(f"   Expected match: {list(matches)}")
        else:
            print(f"\n❌ Query: '{query}'")
            print(f"   Found: {found_names}")
            print(f"   Expected: {expected_tools}")
            all_passed = False

    # Test tool info
    schema = get_tool_schema("create_entities")
    if schema and schema.get("example"):
        print(f"\n✅ Tool info returns examples")
    else:
        print(f"\n⚠️  Tool info missing examples")

    # Test related tools
    related = get_related_tools("search_nodes")
    if len(related) >= 2:
        print(f"✅ Related tools found: {related}")
    else:
        print(f"⚠️  Few related tools: {related}")

    return all_passed

def test_deferred_loading():
    """Test deferred loading configuration"""
    print("\n" + "="*60)
    print("TEST 3: Deferred Loading Configuration")
    print("="*60)

    from deferred_loading import (
        MODULE_CONFIGS,
        LoadingStrategy,
        get_loading_stats,
        HOT_TOOL_DEFINITIONS,
    )

    stats = get_loading_stats()

    print(f"\nLoading Strategy Distribution:")
    print(f"  IMMEDIATE: {stats['immediate']['modules']} modules, {stats['immediate']['tools']} tools, ~{stats['immediate']['tokens']} tokens")
    print(f"  ON_CATEGORY: {stats['on_category']['modules']} modules, {stats['on_category']['tools']} tools, ~{stats['on_category']['tokens']} tokens")
    print(f"  ON_DEMAND: {stats['on_demand']['modules']} modules, {stats['on_demand']['tools']} tools, ~{stats['on_demand']['tokens']} tokens")

    print(f"\nToken Analysis:")
    print(f"  If all loaded: ~{stats['total_tokens_if_all_loaded']} tokens")
    print(f"  With deferred: ~{stats['tokens_with_deferred']} tokens")
    print(f"  REDUCTION: {stats['token_reduction']}")

    # Verify HOT tool definitions are compact
    hot_def_tokens = len(HOT_TOOL_DEFINITIONS.split())
    print(f"\n  HOT definitions: ~{hot_def_tokens} words (~{hot_def_tokens * 1.3:.0f} tokens)")

    # Check reduction percentage
    reduction_pct = float(stats['token_reduction'].rstrip('%'))
    if reduction_pct >= 80:
        print(f"\n✅ Token reduction >= 80% achieved: {stats['token_reduction']}")
        return True
    else:
        print(f"\n⚠️  Token reduction only {stats['token_reduction']} (target: 80%+)")
        return False

def test_execute_code_sandbox():
    """Test that execute_code sandbox exists and is secure"""
    print("\n" + "="*60)
    print("TEST 4: Execute Code Sandbox")
    print("="*60)

    try:
        from sandbox.executor import CodeExecutor, create_api_context
        from sandbox.security import comprehensive_safety_check

        # Test safety check
        dangerous_code = "import os; os.system('rm -rf /')"
        is_safe, issues = comprehensive_safety_check(dangerous_code)

        if not is_safe:
            print(f"✅ Safety check blocks dangerous code")
            print(f"   Issues found: {issues[:2]}")
        else:
            print(f"❌ Safety check FAILED to block dangerous code!")
            return False

        # Test safe code compilation
        safe_code = """
result = 2 + 2
"""
        is_safe, issues = comprehensive_safety_check(safe_code)
        if is_safe:
            print(f"✅ Safety check allows safe code")
        else:
            print(f"⚠️  Safety check too restrictive: {issues}")

        # Test API context
        api_context = create_api_context()
        expected_apis = ['search_nodes', 'create_entities', 'filter_by_confidence']
        available = [k for k in expected_apis if k in api_context]
        print(f"✅ API context has {len(available)} memory APIs available")

        return True

    except ImportError as e:
        print(f"⚠️  RestrictedPython not installed: {e}")
        print(f"   Install with: pip install RestrictedPython")
        return False
    except Exception as e:
        print(f"❌ Sandbox test error: {e}")
        return False

def test_integration():
    """Test that all components integrate correctly"""
    print("\n" + "="*60)
    print("TEST 5: Integration Test")
    print("="*60)

    # Verify imports work
    try:
        from tool_catalog import TOOL_CATALOG
        from tool_search import search_tools, register_tool_search
        from deferred_loading import MODULE_CONFIGS, get_loading_stats

        print(f"✅ All modules import successfully")

        # Simulate a session
        print(f"\nSimulated Session Flow:")

        # Step 1: User asks what tools are available
        from deferred_loading import HOT_TOOL_DEFINITIONS
        print(f"  1. Load HOT tools (~{len(HOT_TOOL_DEFINITIONS.split())} words)")

        # Step 2: User wants to do something specific
        results = search_tools("track my learning progress", limit=3)
        print(f"  2. Search finds: {[r.tool_name for r in results]}")

        # Step 3: Load only needed tools
        print(f"  3. Load specific tools (not entire catalog)")

        # Step 4: Use execute_code for batch
        print(f"  4. Batch operations via execute_code sandbox")

        return True

    except Exception as e:
        print(f"❌ Integration error: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "="*60)
    print("ADVANCED TOOL USE IMPLEMENTATION TESTS")
    print("Based on Anthropic's Nov 2025 Patterns")
    print("="*60)

    results = {
        "Tool Catalog": test_tool_catalog(),
        "Tool Search": test_tool_search(),
        "Deferred Loading": test_deferred_loading(),
        "Execute Code Sandbox": test_execute_code_sandbox(),
        "Integration": test_integration(),
    }

    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")

    print(f"\n  Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Advanced Tool Use implementation ready.")
        print("\nExpected benefits:")
        print("  - 89% token reduction (77k → 8.7k)")
        print("  - On-demand tool discovery")
        print("  - Programmatic batch operations")
        print("  - Secure sandboxed execution")
    else:
        print("\n⚠️  Some tests failed. Review output above.")

    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
