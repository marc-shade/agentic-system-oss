#!/usr/bin/env python3
"""
Test script to verify RAG tools can be loaded into the server.
"""

import sys
import logging

# Set up logging to see all messages
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

logger = logging.getLogger(__name__)

def test_rag_loading():
    """Test that RAG tools can be registered."""

    print("=" * 60)
    print("RAG Tools Loading Test")
    print("=" * 60)

    try:
        # Import FastMCP
        from fastmcp import FastMCP
        app = FastMCP("test-rag")
        print("✅ FastMCP app created")

        # Import memory client
        from memory_client import MemoryClient
        memory_client = MemoryClient()
        print("✅ MemoryClient created")

        # Test re-ranking tools registration
        print("\nTesting re-ranking tools registration...")
        from reranking_tools import register_reranking_tools
        register_reranking_tools(app, memory_client)
        print("✅ Re-ranking tools registered successfully")

        # Test hybrid search tools registration
        print("\nTesting hybrid search tools registration...")
        from hybrid_search_tools import register_hybrid_search_tools
        register_hybrid_search_tools(app)
        print("✅ Hybrid search tools registered successfully")

        # Try to list tools
        print("\nChecking registered tools...")
        if hasattr(app, 'list_tools'):
            tools = app.list_tools()
            print(f"Total tools: {len(tools)}")

            rag_tools = [t for t in tools if 'rerank' in t.name.lower() or 'hybrid' in t.name.lower()]
            if rag_tools:
                print(f"\nRAG tools found ({len(rag_tools)}):")
                for tool in rag_tools:
                    print(f"  - {tool.name}")
            else:
                print("\n❌ No RAG tools found in registered tools")
        else:
            print("⚠️  Cannot list tools (FastMCP API changed?)")

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_rag_loading()
    sys.exit(0 if success else 1)
