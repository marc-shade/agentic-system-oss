#!/usr/bin/env python3
"""
Test script for GraphRAG integration with enhanced-memory MCP.

Tests:
1. Module imports correctly
2. GraphRAG instance creation
3. Tool registration
4. Basic API calls
"""
import platform

import os
import sys
from pathlib import Path

# Add enhanced-memory MCP to path
sys.path.insert(0, str(Path(__file__).parent))

# Storage path from environment
AGENTIC_SYSTEM_PATH = os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE))
GRAPH_RAG_PATH = f"{AGENTIC_SYSTEM_PATH}/scripts/graph-rag.py"

def test_imports():
    """Test that all required modules import"""
    print("Testing imports...")

    try:
        from graphrag_tools import register_graphrag_tools
        print("✅ graphrag_tools module imports")
    except Exception as e:
        print(f"❌ Failed to import graphrag_tools: {e}")
        return False

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "graph_rag",
            GRAPH_RAG_PATH
        )
        graph_rag_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(graph_rag_module)
        GraphRAG = graph_rag_module.GraphRAG
        print("✅ GraphRAG class imports from scripts")
    except Exception as e:
        print(f"❌ Failed to import GraphRAG: {e}")
        return False

    return True


def test_graphrag_creation():
    """Test GraphRAG instance creation"""
    print("\nTesting GraphRAG instance creation...")

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "graph_rag",
            GRAPH_RAG_PATH
        )
        graph_rag_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(graph_rag_module)
        GraphRAG = graph_rag_module.GraphRAG

        # Create instance
        db_path = Path.home() / ".claude" / "enhanced_memories" / "memory.db"
        if not db_path.exists():
            print(f"⚠️  Database doesn't exist yet: {db_path}")
            print("   This is OK - it will be created on first use")

        rag = GraphRAG(db_path=db_path)
        print(f"✅ GraphRAG instance created with DB: {db_path}")

        # Test statistics
        stats = rag.get_statistics()
        print(f"✅ Graph statistics: {stats['entities']} entities, {stats['relationships']} relationships")

        return True

    except Exception as e:
        print(f"❌ Failed to create GraphRAG instance: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tool_registration():
    """Test that tools can be registered (mock FastMCP app)"""
    print("\nTesting tool registration...")

    try:
        from graphrag_tools import register_graphrag_tools

        # Create mock FastMCP app
        class MockApp:
            def __init__(self):
                self.tools = []

            def tool(self):
                """Decorator to register tools"""
                def decorator(func):
                    self.tools.append(func.__name__)
                    return func
                return decorator

        mock_app = MockApp()

        # Register tools
        db_path = Path.home() / ".claude" / "enhanced_memories" / "memory.db"
        rag_instance = register_graphrag_tools(mock_app, db_path)

        print(f"✅ Registered {len(mock_app.tools)} tools:")
        for tool_name in mock_app.tools:
            print(f"   - {tool_name}")

        expected_tools = [
            'graph_enhanced_search',
            'get_entity_neighbors',
            'add_entity_relationship',
            'get_graph_statistics',
            'extract_entity_relationships',
            'extract_all_relationships',
            'build_local_graph'
        ]

        for expected in expected_tools:
            if expected in mock_app.tools:
                print(f"✅ Tool '{expected}' registered")
            else:
                print(f"❌ Tool '{expected}' NOT registered")
                return False

        return True

    except Exception as e:
        print(f"❌ Tool registration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_schema():
    """Test that database schema is correct"""
    print("\nTesting database schema...")

    try:
        import sqlite3
        db_path = Path.home() / ".claude" / "enhanced_memories" / "memory.db"

        if not db_path.exists():
            print(f"⚠️  Database doesn't exist yet: {db_path}")
            print("   Schema will be created on first GraphRAG use")
            return True

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check relations table
        cursor.execute("PRAGMA table_info(relations)")
        columns = {row[1] for row in cursor.fetchall()}

        required_columns = {'id', 'from_entity_id', 'to_entity_id', 'relation_type', 'weight', 'is_causal', 'context'}

        for col in required_columns:
            if col in columns:
                print(f"✅ Column '{col}' exists in relations table")
            else:
                print(f"⚠️  Column '{col}' missing - will be added on first use")

        # Check indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='relations'")
        indexes = [row[0] for row in cursor.fetchall()]

        if indexes:
            print(f"✅ Found {len(indexes)} indexes on relations table")
            for idx in indexes:
                print(f"   - {idx}")
        else:
            print("⚠️  No indexes yet - will be created on first use")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Database schema check failed: {e}")
        import traceback

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()

        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("GraphRAG Integration Test Suite")
    print("=" * 60)

    tests = [
        ("Module Imports", test_imports),
        ("GraphRAG Instance Creation", test_graphrag_creation),
        ("Tool Registration", test_tool_registration),
        ("Database Schema", test_database_schema)
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n{'=' * 60}")
        print(f"Running: {test_name}")
        print('=' * 60)
        result = test_func()
        results.append((test_name, result))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! GraphRAG integration is ready.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
